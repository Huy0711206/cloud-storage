"""One upload lifecycle for personal, team and upload-only request scopes."""
from datetime import timedelta
import hashlib
import mimetypes
import os
from app.core.models import utcnow
from app.features.billing.entitlements import require_feature
from . import native_service as s
from .access import scope_guard, scoped_node, scoped_parent, team_node_ids
from .native_models import UploadSession, FileNode
from .collaboration_models import TeamUpload, RequestUpload
from .version_models import ReplacementUpload
from .capacity import ensure_storage_capacity


def _request_limits(db, request, size):
    from .request_service import request_usage
    if not 0 <= size <= request.max_file_size:
        raise s.StorageError(413, "Tệp vượt kích thước cho phép của yêu cầu.")
    budget = request_usage(db, request)
    if budget["used_bytes"] + budget["reserved_bytes"] + size > request.max_total_size:
        raise s.StorageError(413, "Yêu cầu đã hết dung lượng tiếp nhận.")
    query = db.query(RequestUpload).filter_by(request_id=request.id)
    if query.filter(RequestUpload.created_at > utcnow()-timedelta(hours=1)).count() >= 20 or query.count() >= 200:
        raise s.StorageError(429, "Yêu cầu đã đạt giới hạn lượt gửi. Hãy thử sau hoặc liên hệ người nhận.")


def _upload(db, owner, team, request, actor, upload_id, *, pending=True, abort=False):
    row = db.query(UploadSession).filter_by(id=upload_id, owner_id=owner.id).populate_existing().with_for_update().first()
    if not row:
        raise s.StorageError(404, "Không tìm thấy phiên tải lên.")
    group = db.query(TeamUpload).filter_by(upload_id=row.id).populate_existing().first()
    inbox = db.query(RequestUpload).filter_by(upload_id=row.id).populate_existing().first()
    if team:
        valid = group and group.team_id == team.id and group.user_id == actor.id and not inbox
    elif request:
        valid = inbox and inbox.request_id == request.id and not group
    else:
        valid = not group and not inbox
        if abort and row.parent_id in team_node_ids(db, owner.id):
            valid = False
    if not valid:
        raise s.StorageError(404, "Không tìm thấy phiên tải lên trong phạm vi này.")
    if not abort:
        scoped_parent(db, owner, team, row.parent_id)
        if request and row.parent_id != request.parent_id:
            raise s.StorageError(409, "Vị trí nhận tệp đã thay đổi.")
        if row.node_id:
            scoped_node(db, owner, team, row.node_id)
        replacement = db.get(ReplacementUpload, row.id)
        if replacement:
            scoped_node(db, owner, team, replacement.node_id)
    if pending and (row.state != "pending" or row.expires_at <= utcnow()):
        raise s.StorageError(409, "Phiên tải lên đã đóng hoặc hết hạn.")
    return row


def start_upload(db, actor, name, parent_id, size, replace_node_id=None, *, team_id=None, request_token=None):
    with scope_guard(db, actor, team_id=team_id, request_token=request_token, write=True) as (owner, team, request):
        if size < 0 or size > 2**63-1:
            raise s.StorageError(400, "Kích thước tệp không hợp lệ.")
        name = s.valid_name(name)
        if request:
            if replace_node_id:
                raise s.StorageError(403, "Yêu cầu nhận tệp không cho phép thay thế nội dung.")
            parent_id = request.parent_id
            _request_limits(db, request, size)
        parent_id = scoped_parent(db, owner, team, parent_id)
        target = None
        if replace_node_id:
            require_feature(owner, "versions")
            target = scoped_node(db, owner, team, replace_node_id)
            if target.is_folder or target.name != name or target.parent_id != parent_id:
                raise s.StorageError(409, "Hãy chọn đúng tệp hiện tại để thay thế; tên và thư mục phải khớp.")
            if not target.blob_key or not s.blob_path(target.blob_key).is_file():
                raise s.StorageError(503, "Bản hiện tại chưa khả dụng; chưa thể thay thế an toàn.")
        else:
            s.assert_available(db, owner.id, parent_id, name)
        s.expire_uploads(db, owner.id)
        if db.query(UploadSession).filter_by(owner_id=owner.id, state="pending").count() >= 200:
            raise s.StorageError(429, "Đang có quá nhiều phiên tải lên. Hãy hoàn tất hoặc hủy các phiên cũ.")
        if size > s.quota_usage(db, owner)["available"]:
            raise s.StorageError(413, "Không đủ dung lượng. Hãy giải phóng bộ nhớ hoặc nâng cấp gói.")
        ensure_storage_capacity(db, size)
        path = None
        created = False
        try:
            deadline = utcnow()+timedelta(hours=24)
            row = UploadSession(owner_id=owner.id, parent_id=parent_id, name=name, size=size,
                                expires_at=min(deadline, request.expires_at) if request else deadline)
            db.add(row)
            db.flush()
            upload_id = row.id
            if team:
                db.add(TeamUpload(upload_id=row.id, team_id=team.id, user_id=actor.id))
            if request:
                db.add(RequestUpload(upload_id=row.id, request_id=request.id))
            if target:
                db.add(ReplacementUpload(upload_id=row.id, node_id=target.id, expected_blob_key=target.blob_key))
            db.flush()
            path = s.upload_path(row.id)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch(exist_ok=False)
            created = True
            db.commit()
        except Exception:
            db.rollback()
            if created:
                try:
                    persisted = db.query(UploadSession).filter_by(id=upload_id).populate_existing().first()
                except Exception:
                    # Preserve bytes if commit outcome cannot be established.
                    persisted = True
                if not persisted:
                    path.unlink(missing_ok=True)
            raise
        return {"id":row.id,"chunk_size":s.CHUNK_SIZE,"received":0,"size":size}


def append_chunk(db, actor, upload_id, data, offset, *, team_id=None, request_token=None):
    with scope_guard(db, actor, team_id=team_id, request_token=request_token, write=True) as (owner, team, request):
        row = _upload(db, owner, team, request, actor, upload_id)
        if len(data) > s.CHUNK_SIZE:
            raise s.StorageError(413, "Mỗi phần tải lên tối đa 8 MB.")
        if offset is None:
            raise s.StorageError(400, "Thiếu Upload-Offset.")
        if offset != row.received:
            raise s.StorageError(409, f"Vị trí tải lên không khớp; vị trí hiện tại: {row.received}.")
        if row.received+len(data) > row.size:
            raise s.StorageError(400, "Dữ liệu vượt kích thước đã khai báo.")
        path = s.upload_path(row.id)
        if not path.is_file() or path.stat().st_size < row.received:
            raise s.StorageError(409, "Tệp tải lên chưa hoàn tất không còn hợp lệ. Hãy tải lại.")
        # Repair bytes not acknowledged by a successful metadata commit.
        with path.open("r+b") as stream:
            stream.truncate(row.received)
            stream.seek(row.received)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        row.received += len(data)
        db.commit()
        return {"received":row.received,"size":row.size}


def finish_upload(db, actor, upload_id, *, team_id=None, request_token=None):
    with scope_guard(db, actor, team_id=team_id, request_token=request_token, write=True) as (owner, team, request):
        row = _upload(db, owner, team, request, actor, upload_id, pending=False)
        if row.state == "complete" and row.node_id:
            return s.serialize_node(scoped_node(db, owner, team, row.node_id))
        if row.state != "pending" or row.expires_at <= utcnow():
            raise s.StorageError(409, "Phiên tải lên đã đóng hoặc hết hạn.")
        if row.received != row.size:
            raise s.StorageError(409, "Tệp chưa tải lên đầy đủ.")
        replacement = db.get(ReplacementUpload, row.id)
        target = benefits = None
        if replacement:
            benefits = require_feature(owner, "versions")
            target = scoped_node(db, owner, team, replacement.node_id)
            if target.blob_key != replacement.expected_blob_key or target.name != row.name or target.parent_id != row.parent_id:
                raise s.StorageError(409, "Tệp đã thay đổi trong lúc tải lên. Hãy tải lại phiên bản hiện tại trước khi thay thế.")
        else:
            s.assert_available(db, owner.id, row.parent_id, row.name)
        usage = s.quota_usage(db, owner)
        if usage["used"]+usage["reserved"] > usage["total"]:
            raise s.StorageError(413, "Hạn mức hiện tại không đủ để hoàn tất tải lên.")
        ensure_storage_capacity(db, 0)
        path = s.upload_path(row.id)
        destination = s.blob_path(row.id)
        destination.parent.mkdir(parents=True, exist_ok=True)
        source = path if path.is_file() else destination
        if not source.is_file() or source.stat().st_size != row.size:
            raise s.StorageError(409, "Tệp tải lên không đầy đủ.")
        digest = hashlib.sha256()
        with source.open("rb") as stream:
            for block in iter(lambda:stream.read(1024*1024), b""):
                digest.update(block)
        if source == path:
            os.replace(path, destination)
        try:
            if target:
                from .version_service import archive_current
                archive_current(db, owner, target, benefits)
                node = target
                node.blob_key = row.id
                node.size = row.size
                node.sha256 = digest.hexdigest()
                node.modified_at = utcnow()
                node.mime_type = mimetypes.guess_type(row.name)[0] or "application/octet-stream"
            else:
                node = FileNode(owner_id=owner.id, parent_id=row.parent_id, name=row.name, is_folder=False,
                                size=row.size, blob_key=row.id, sha256=digest.hexdigest(),
                                mime_type=mimetypes.guess_type(row.name)[0] or "application/octet-stream")
                db.add(node)
            db.flush()
            row.state, row.node_id = "complete", node.id
            db.commit()
        except Exception:
            db.rollback()
            # Keep stable destination bytes: a lost commit acknowledgement may have
            # committed metadata; pending sessions can also resume from this location.
            raise
        return s.serialize_node(node)


def abort_upload(db, actor, upload_id, *, team_id=None, request_token=None):
    with scope_guard(db, actor, team_id=team_id, request_token=request_token, write=True, allow_closed=True) as (owner, team, request):
        row = _upload(db, owner, team, request, actor, upload_id, pending=False, abort=True)
        if row.state == "pending":
            row.state = "aborted"
            s.upload_path(row.id).unlink(missing_ok=True)
            s.blob_path(row.id).unlink(missing_ok=True)
        db.commit()
        return {"ok":True}
