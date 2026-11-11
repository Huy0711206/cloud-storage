"""Native storage operations. Mutations serialize on the owning User row in PostgreSQL."""
from contextlib import contextmanager, ExitStack
import os
from pathlib import Path
import re
import threading
import unicodedata

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.models import User, Plan, utcnow
from .native_models import FileNode, FileShare, StorageGarbage, UploadSession, identifier
from .migration_models import FileVersion

CHUNK_SIZE = 8 * 1024 * 1024
_owner_locks: dict[int, threading.RLock] = {}
_lock_map_guard = threading.Lock()


class StorageError(Exception):
    def __init__(self, status: int, detail: str):
        self.status, self.detail = status, detail


def storage_root() -> Path:
    return Path(os.environ.get("STORAGE_ROOT", "/data/cloudbox")).resolve()


def blob_path(key: str) -> Path:
    if not re.fullmatch(r"[a-f0-9]{32}", key or ""):
        raise StorageError(400, "Mã tệp không hợp lệ.")
    return storage_root() / "blobs" / key[:2] / key


def upload_path(key: str) -> Path:
    if not re.fullmatch(r"[a-f0-9]{32}", key or ""):
        raise StorageError(400, "Mã phiên tải lên không hợp lệ.")
    return storage_root() / "uploads" / key


@contextmanager
def owner_lock(db: Session, owner_id: int, actor_id: int | None = None):
    # Stable ordering protects a team actor and sponsor without cross-team deadlocks.
    ids = sorted({owner_id, actor_id if actor_id is not None else owner_id})
    with _lock_map_guard:
        locks = [_owner_locks.setdefault(key, threading.RLock()) for key in ids]
    with ExitStack() as stack:
        for lock in locks:
            stack.enter_context(lock)
        try:
            owners = {key: lock_owner(db,key) for key in ids}
            yield owners
        except Exception:
            db.rollback()
            raise


@contextmanager
def owner_guard(db: Session, owner_id: int, actor_id: int | None = None):
    with owner_lock(db,owner_id,actor_id) as owners:
        if any(not owner.is_active or not owner.is_verified for owner in owners.values()):
            raise StorageError(403, "Tài khoản chưa được xác minh hoặc đã bị khóa.")
        yield


def lock_owner(db: Session, owner_id: int) -> User:
    user = db.query(User).filter_by(id=owner_id).populate_existing().with_for_update().first()
    if not user:
        raise StorageError(401, "Vui lòng đăng nhập.")
    db.expire(user, ["plan"])
    if user.plan_id is not None:
        db.query(Plan).filter_by(id=user.plan_id).populate_existing().first()
    return user


def valid_name(value: str) -> str:
    name = unicodedata.normalize("NFC", value.strip())
    if not name or len(name) > 255 or name in (".", "..") or any(c in name for c in "/\\\x00") or any(ord(c) < 32 or ord(c) == 127 for c in name):
        raise StorageError(400, "Tên phải có 1–255 ký tự, không chứa dấu phân cách đường dẫn hoặc ký tự điều khiển.")
    return name


def owned_node(db: Session, owner_id: int, node_id: str, deleted: bool = False) -> FileNode:
    n = db.query(FileNode).filter_by(id=node_id, owner_id=owner_id).populate_existing().first()
    if not n or (not deleted and n.deleted_at is not None):
        raise StorageError(404, "Không tìm thấy tệp hoặc thư mục.")
    return n


def parent_folder(db: Session, owner_id: int, parent_id: str | None):
    if parent_id:
        n = owned_node(db, owner_id, parent_id)
        if not n.is_folder:
            raise StorageError(400, "Vị trí đích phải là thư mục.")
        return n
    return None


def assert_available(db: Session, owner_id: int, parent_id: str | None, name: str, excluding: str | None = None):
    q = db.query(FileNode).filter_by(owner_id=owner_id, parent_id=parent_id, name=name).filter(FileNode.deleted_at.is_(None))
    if excluding:
        q = q.filter(FileNode.id != excluding)
    if q.first():
        raise StorageError(409, "Đã có tệp hoặc thư mục cùng tên tại vị trí này.")


def quota_usage(db: Session, user: User) -> dict:
    used = int(db.query(func.coalesce(func.sum(FileNode.size), 0)).filter_by(owner_id=user.id, is_folder=False).scalar() or 0)
    versions = int(db.query(func.coalesce(func.sum(FileVersion.size), 0)).filter(FileVersion.owner_id==user.id,FileVersion.blob_key.is_not(None)).scalar() or 0)
    used += versions
    reserved = int(db.query(func.coalesce(func.sum(UploadSession.size), 0)).filter_by(owner_id=user.id, state="pending").filter(UploadSession.expires_at > utcnow()).scalar() or 0)
    from app.features.billing.entitlements import effective_plan
    plan = effective_plan(user)
    free = db.query(Plan).filter_by(code="free").populate_existing().first() if not plan else None
    total = int(plan.quota_gb if plan else ((free.quota_gb if free else 1) if user.plan or user.role=="admin" else 0)) * 1024**3
    return {"used": used, "total": total, "reserved": reserved, "available": max(0, total-used-reserved), "percent": min(100, round(100 * used/total)) if total else 0, "trash_counts": True,"versions_counts":True,"versions_used":versions}


def serialize_node(node: FileNode) -> dict:
    return {"id": node.id, "name": node.name, "is_folder": node.is_folder, "parent_id": node.parent_id,
            "size": node.size, "modified_at": node.modified_at.isoformat()+"Z", "deleted_at": node.deleted_at.isoformat()+"Z" if node.deleted_at else None,
            "mime_type": node.mime_type, "sha256": node.sha256}


def descendants(db: Session, node: FileNode, include_deleted: bool = False) -> list[FileNode]:
    result, frontier, seen = [node], [node.id], {node.id}
    while frontier:
        q = db.query(FileNode).filter(FileNode.owner_id == node.owner_id, FileNode.parent_id.in_(frontier))
        if not include_deleted:
            q = q.filter(FileNode.deleted_at.is_(None))
        children = [n for n in q.populate_existing().all() if n.id not in seen]
        seen.update(n.id for n in children)
        result.extend(children)
        frontier = [n.id for n in children]
    return result


def ancestor_nodes(db: Session, owner_id: int, parent_id: str | None) -> list[dict]:
    result, seen = [], set()
    while parent_id:
        if parent_id in seen:
            raise StorageError(409, "Cấu trúc thư mục không hợp lệ.")
        seen.add(parent_id)
        n = owned_node(db, owner_id, parent_id)
        result.append({"id": n.id, "name": n.name})
        parent_id = n.parent_id
    return list(reversed(result))


def list_nodes(db: Session, user: User, parent_id: str | None, search: str = "", trash: bool = False, sort: str = "name", offset:int=0,limit:int=200):
    from .access import fresh_user, scoped_parent, team_node_ids
    user = fresh_user(db,user.id)
    scoped_parent(db,user,None,parent_id)
    q = db.query(FileNode).filter_by(owner_id=user.id)
    hidden = team_node_ids(db,user.id)
    if hidden:q=q.filter(FileNode.id.notin_(hidden))
    if trash:
        q = q.filter(FileNode.deleted_at.is_not(None), FileNode.trash_root_id == FileNode.id)
    else:
        q = q.filter(FileNode.deleted_at.is_(None))
        if not search:
            q = q.filter(FileNode.parent_id == parent_id)
    if search:
        q = q.filter(FileNode.name.ilike("%"+search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")+"%", escape="\\"))
    order = {"name": FileNode.name.asc(), "name_desc": FileNode.name.desc(), "size": FileNode.size.desc(), "modified": FileNode.modified_at.desc()}.get(sort, FileNode.name.asc())
    offset=max(0,offset);limit=min(500,max(1,limit));count=q.count()
    nodes = q.order_by(FileNode.is_folder.desc(), order, FileNode.id).offset(offset).limit(limit).all()
    next_offset=offset+len(nodes)
    return {"items": [serialize_node(n) for n in nodes], "ancestors": ancestor_nodes(db,user.id,parent_id), "usage": quota_usage(db,user), "limit":limit,"offset":offset,"has_more":next_offset<count,"next_offset":next_offset if next_offset<count else None,"total_count":count}


def create_folder(db: Session, user: User, name: str, parent_id: str | None, *, team_id: str | None = None):
    from .access import scope_guard, scoped_node, scoped_parent
    with scope_guard(db,user,team_id=team_id,write=True) as (user,team,_):
        name = valid_name(name)
        parent_id = scoped_parent(db,user,team,parent_id)
        assert_available(db,user.id,parent_id,name)
        n = FileNode(owner_id=user.id,parent_id=parent_id,name=name,is_folder=True)
        db.add(n); db.commit()
        return serialize_node(n)


def update_node(db: Session, user: User, node_id: str, changes: dict, *, team_id: str | None = None):
    from .access import scope_guard, scoped_node, scoped_parent
    with scope_guard(db,user,team_id=team_id,write=True) as (user,team,_):
        n = scoped_node(db,user,team,node_id,mutable=True)
        name = valid_name(changes.get("name", n.name))
        parent = changes.get("parent_id", n.parent_id)
        parent = scoped_parent(db,user,team,parent)
        if parent in {x.id for x in descendants(db,n,True)}:
            raise StorageError(409,"Không thể di chuyển thư mục vào chính nó hoặc thư mục con.")
        assert_available(db,user.id,parent,name,n.id)
        n.name, n.parent_id, n.modified_at = name, parent, utcnow()
        db.commit()
        return serialize_node(n)


def trash_node(db: Session, user: User, node_id: str, *, team_id: str | None = None):
    from .access import scope_guard, scoped_node, scoped_parent
    with scope_guard(db,user,team_id=team_id,write=True) as (user,team,_):
        n = scoped_node(db,user,team,node_id,mutable=True)
        now = utcnow()
        for child in descendants(db,n):
            child.deleted_at, child.trash_root_id = now,n.id
        db.commit()
        return {"ok":True,"usage":quota_usage(db,user)}


def restore_node(db: Session, user: User, node_id: str, *, team_id: str | None = None):
    from .access import scope_guard, scoped_node, scoped_parent
    with scope_guard(db,user,team_id=team_id,write=True) as (user,team,_):
        n = scoped_node(db,user,team,node_id,True,mutable=True)
        if not n.deleted_at or n.trash_root_id != n.id:
            raise StorageError(409,"Hãy khôi phục thư mục gốc trong thùng rác.")
        if n.parent_id:
            p = db.query(FileNode).filter_by(id=n.parent_id).populate_existing().first()
            if not p or p.deleted_at:
                n.parent_id = team.root_id if team else None
        n.parent_id = scoped_parent(db,user,team,n.parent_id)
        assert_available(db,user.id,n.parent_id,n.name,n.id)
        for child in db.query(FileNode).filter_by(owner_id=user.id,trash_root_id=n.id).all():
            child.deleted_at = child.trash_root_id = None
            child.modified_at = utcnow()
        db.commit()
        return serialize_node(n)


def collect_garbage(db: Session, limit: int = 100) -> int:
    """Retry committed deletion jobs. Never visits the retained Nextcloud source."""
    count=0
    for job in db.query(StorageGarbage).order_by(StorageGarbage.created_at).limit(limit).with_for_update(skip_locked=True).all():
        try:
            if job.kind=="upload":upload_path(job.object_key).unlink(missing_ok=True)
            elif job.kind=="blob":
                # Fail closed if a reference exists; a bad job must never erase live bytes.
                if db.query(FileNode).filter_by(blob_key=job.object_key).first() or db.query(FileVersion).filter_by(blob_key=job.object_key).first():continue
                blob_path(job.object_key).unlink(missing_ok=True)
            else:continue
        except OSError:continue
        db.delete(job);count+=1
    db.commit()
    return count


def purge_node(db: Session, user: User, node_id: str, confirm_id: str, *, team_id: str | None = None):
    if confirm_id!=node_id:raise StorageError(400,"Vui lòng xác nhận đúng mục cần xóa vĩnh viễn.")
    from .access import scope_guard, scoped_node, scoped_parent
    with scope_guard(db,user,team_id=team_id,write=True) as (user,team,_):
        root=scoped_node(db,user,team,node_id,True,mutable=True)
        if not root.deleted_at or root.trash_root_id!=root.id:raise StorageError(409,"Chỉ có thể xóa vĩnh viễn mục gốc trong thùng rác.")
        nodes=descendants(db,root,True)
        ids=[n.id for n in nodes]
        keys={n.blob_key for n in nodes if n.blob_key}
        versions=db.query(FileVersion).filter(FileVersion.owner_id==user.id,FileVersion.node_id.in_(ids)).all()
        keys.update(v.blob_key for v in versions if v.blob_key)
        uploads=db.query(UploadSession).filter(UploadSession.owner_id==user.id,UploadSession.parent_id.in_(ids)).with_for_update().all()
        for upload in uploads:
            if upload.state=="pending":
                upload.state="aborted"
                db.add(StorageGarbage(kind="upload",object_key=upload.id))
                db.add(StorageGarbage(kind="blob",object_key=upload.id))
            upload.parent_id=None
        db.flush()
        db.query(FileShare).filter(FileShare.owner_id==user.id,FileShare.node_id.in_(ids)).delete(synchronize_session=False)
        db.query(FileVersion).filter(FileVersion.owner_id==user.id,FileVersion.node_id.in_(ids)).delete(synchronize_session=False)
        # A single statement permits PostgreSQL to check self-FKs after all subtree rows are removed.
        db.query(FileNode).filter(FileNode.owner_id==user.id,FileNode.id.in_(ids)).delete(synchronize_session=False)
        for key in keys:db.add(StorageGarbage(kind="blob",object_key=key))
        db.commit()
    collect_garbage(db,max(100,len(keys)+len(uploads)*2))
    remaining=db.query(StorageGarbage).count()
    return {"ok":True,"purged_count":len(ids),"cleanup_pending":remaining>0,"usage":quota_usage(db,user)}


def expire_uploads(db: Session, owner_id: int | None = None) -> int:
    q=db.query(UploadSession).filter(UploadSession.state=="pending", UploadSession.expires_at<=utcnow())
    if owner_id is not None:q=q.filter_by(owner_id=owner_id)
    rows=q.with_for_update().all()
    for upload in rows:
        upload.state="expired"
        upload_path(upload.id).unlink(missing_ok=True)
        blob_path(upload.id).unlink(missing_ok=True)
    db.flush()
    return len(rows)


# Compatibility interface: all scopes execute the same lifecycle implementation.
def start_upload(db, user, name, parent_id, size, replace_node_id=None, *, team_id=None, request_token=None):
    from .uploads import start_upload as operation
    return operation(db,user,name,parent_id,size,replace_node_id,team_id=team_id,request_token=request_token)


def append_chunk(db, user, upload_id, data, offset, *, team_id=None, request_token=None):
    from .uploads import append_chunk as operation
    return operation(db,user,upload_id,data,offset,team_id=team_id,request_token=request_token)


def finish_upload(db, user, upload_id, *, team_id=None, request_token=None):
    from .uploads import finish_upload as operation
    return operation(db,user,upload_id,team_id=team_id,request_token=request_token)


def abort_upload(db, user, upload_id, *, team_id=None, request_token=None):
    from .uploads import abort_upload as operation
    return operation(db,user,upload_id,team_id=team_id,request_token=request_token)


def create_share(db:Session,user:User,node_id:str,expires_at=None,password=None):
    from .share_service import create
    return create(db,user,node_id,expires_at,password)


def list_shares(db:Session,user:User,node_id:str):
    from .access import personal_node, fresh_user
    user=fresh_user(db,user.id)
    personal_node(db,user,node_id)
    from .share_service import metadata
    return [{**metadata(db,user,s),"id":s.id,"created_at":s.created_at.isoformat()+"Z","revoked":s.revoked_at is not None,"permission":"read"} for s in db.query(FileShare).filter_by(owner_id=user.id,node_id=node_id).order_by(FileShare.created_at.desc()).all()]


def all_shares(db:Session,user:User):
    from .access import fresh_user, team_node_ids
    user=fresh_user(db,user.id)
    hidden=team_node_ids(db,user.id)
    from .share_service import metadata
    return {"items":[{**metadata(db,user,share),"id":share.id,"file_id":node.id,"name":node.name,"is_folder":node.is_folder,"created_at":share.created_at.isoformat()+"Z","permission":"read","revoked":share.revoked_at is not None}
                     for share,node in db.query(FileShare,FileNode).join(FileNode,FileShare.node_id==FileNode.id).filter(FileShare.owner_id==user.id,FileShare.node_id.notin_(hidden)).order_by(FileShare.created_at.desc()).all()]}


def revoke_share(db:Session,user:User,share_id:str):
    from .access import scope_guard, scoped_node
    with scope_guard(db,user,write=True) as (user,_,__):
        s=db.query(FileShare).filter_by(id=share_id,owner_id=user.id).first()
        if not s:raise StorageError(404,"Không tìm thấy liên kết.")
        scoped_node(db,user,None,s.node_id,deleted=True)
        s.revoked_at=utcnow();db.commit();return {"ok":True}


def shared_node(db:Session,root:FileNode,node_id:str):
    from .access import assert_personal_node
    assert_personal_node(db,root.owner_id,root.id)
    assert_personal_node(db,root.owner_id,node_id)
    n=owned_node(db,root.owner_id,node_id)
    cursor=n;seen=set()
    while cursor:
        if cursor.id==root.id:return n
        if cursor.id in seen:break
        seen.add(cursor.id)
        cursor=owned_node(db,root.owner_id,cursor.parent_id) if cursor.parent_id else None
    raise StorageError(404,"Tệp không thuộc liên kết chia sẻ này.")
