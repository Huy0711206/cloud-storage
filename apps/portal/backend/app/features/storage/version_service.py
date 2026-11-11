"""Owner-only native revision snapshots; retention never deletes imported data."""
from datetime import timedelta
import mimetypes
import os
import shutil

from sqlalchemy.orm import Session

from app.core.models import User, utcnow
from app.features.billing.entitlements import benefits_for_user, require_feature
from .migration_models import FileVersion
from .native_models import FileNode, identifier
from .version_models import VersionPolicy
from . import native_service as s
from .access import scope_guard, scoped_node, team_access


def archive_current(db: Session, user: User, node: FileNode, benefits: dict) -> FileVersion:
    """Move the current blob reference into history in the caller's transaction."""
    if (not node.blob_key or not s.blob_path(node.blob_key).is_file()
            or s.blob_path(node.blob_key).stat().st_size != node.size):
        raise s.StorageError(503, "Bản hiện tại tạm thời không khả dụng; chưa thể thay thế an toàn.")
    now = utcnow()
    version = FileVersion(owner_id=user.id, node_id=node.id, source_key="native:" + identifier(),
                          name=node.name, size=node.size, blob_key=node.blob_key,
                          sha256=node.sha256, created_at=now)
    db.add(version)
    db.flush()
    db.add(VersionPolicy(version_id=version.id,
                         expires_at=now + timedelta(days=benefits["version_days"]),
                         plan_code=benefits["code"]))
    return version


def version_access(db: Session, version: FileVersion) -> tuple[bool, object | None, str]:
    imported = not version.source_key.startswith("native:")
    policy = db.get(VersionPolicy, version.id)
    expiry = None if imported else (policy.expires_at if policy else version.created_at)
    # Native history without its creation policy fails closed, never guesses retention.
    within_window = imported or (expiry is not None and expiry > utcnow())
    return bool(version.blob_key and within_window), expiry, "imported" if imported else "native"


def lookup_version(db: Session, user: User, node_id: str, version_id: str, *, team_id=None) -> FileVersion:
    actor=user
    with scope_guard(db,actor,team_id=team_id) as (user,team,_):
        scoped_node(db,user,team,node_id)
        version = db.query(FileVersion).filter_by(id=version_id, node_id=node_id, owner_id=user.id).populate_existing().first()
        if not version or not version.blob_key:
            raise s.StorageError(404, "Không tìm thấy nội dung phiên bản.")
        available, _, _ = version_access(db, version)
        if not available:
            raise s.StorageError(410, "Phiên bản đã hết thời hạn truy cập. Dữ liệu chưa bị tự động xóa.")
        if not s.blob_path(version.blob_key).is_file():
            raise s.StorageError(503, "Phiên bản tạm thời không khả dụng.")
        return version

def list_versions(db: Session, user: User, node_id: str, writable: bool = True, *, team_id=None):
    actor=user
    with scope_guard(db,actor,team_id=team_id) as (user,team,_):
        if team:
            _,_,role=team_access(db,actor,team.id)
            writable=writable and role in ("owner","editor") and benefits_for_user(user)["team_space"]
        scoped_node(db,user,team,node_id)
        rows=db.query(FileVersion).filter_by(owner_id=user.id,node_id=node_id).order_by(FileVersion.created_at.desc()).all()
        items=[]
        days=benefits_for_user(user)["version_days"]
        for version in rows:
            available,expiry,source=version_access(db,version)
            items.append({"id":version.id,"name":version.name,"size":version.size,
                          "created_at":version.created_at.isoformat()+"Z","available":available,
                          "restorable":available and bool(days) and writable,"source":source,
                          "expires_at":expiry.isoformat()+"Z" if expiry else None})
        return {"items":items,"retention_days":days,
                "notice":"Phiên bản và thùng rác tính vào dung lượng. Hết hạn truy cập không tự xóa dữ liệu cũ."}

def restore_version(db: Session, user: User, node_id: str, version_id: str, *, team_id=None):
    created = False
    actor=user
    with scope_guard(db,actor,team_id=team_id,write=True) as (user,team,_):
        benefits = require_feature(user, "versions")
        node = scoped_node(db,user,team,node_id)
        if node.is_folder:
            raise s.StorageError(400, "Thư mục không có phiên bản nội dung.")
        version = lookup_version(db, actor, node_id, version_id,team_id=team_id)
        # The selected history remains readable and the current revision is archived.
        # A fresh blob keeps both snapshots independent, and its full size is charged.
        if version.size > s.quota_usage(db, user)["available"]:
            raise s.StorageError(413, "Không đủ dung lượng để giữ bản hiện tại và khôi phục phiên bản.")
        from .capacity import ensure_storage_capacity
        ensure_storage_capacity(db, version.size)
        key = identifier()
        destination = s.blob_path(key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            with s.blob_path(version.blob_key).open("rb") as source, destination.open("xb") as target:
                created = True
                shutil.copyfileobj(source, target, 1024 * 1024)
                target.flush()
                os.fsync(target.fileno())
            if destination.stat().st_size != version.size:
                raise s.StorageError(503, "Nội dung phiên bản không đầy đủ; chưa thay đổi bản hiện tại.")
            archive_current(db, user, node, benefits)
            node.blob_key, node.sha256, node.size = key, version.sha256, version.size
            node.modified_at = utcnow()
            node.mime_type = mimetypes.guess_type(node.name)[0] or "application/octet-stream"
            db.commit()
        except Exception:
            db.rollback()
            if created:
                try:
                    referenced = (db.query(FileNode).filter_by(blob_key=key).first()
                                  or db.query(FileVersion).filter_by(blob_key=key).first())
                except Exception:
                    # An uncertain commit must not delete potentially live content.
                    referenced = True
                if not referenced:
                    destination.unlink(missing_ok=True)
            raise
        return {"item": s.serialize_node(node), "usage": s.quota_usage(db, user)}
