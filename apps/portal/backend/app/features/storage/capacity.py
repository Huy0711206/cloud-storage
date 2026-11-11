"""Aggregate physical budget, distinct from a customer's logical plan quota."""
import os
import shutil
from sqlalchemy import func, text
from app.core.models import utcnow
from .native_models import FileNode, UploadSession
from .migration_models import FileVersion


def pool_limit():
    return max(0, int(os.environ.get("STORAGE_POOL_LIMIT_BYTES", "0")))


def pool_usage(db):
    current = int(db.query(func.coalesce(func.sum(FileNode.size), 0)).scalar())
    history = int(db.query(func.coalesce(func.sum(FileVersion.size), 0)).filter(FileVersion.blob_key.is_not(None)).scalar())
    pending = db.query(UploadSession).filter(UploadSession.state == "pending", UploadSession.expires_at > utcnow())
    reserved = int(pending.with_entities(func.coalesce(func.sum(UploadSession.size), 0)).scalar())
    limit = pool_limit()
    return {"pool_limit_bytes": limit, "used_bytes": current + history, "reserved_bytes": reserved,
            "available_bytes": max(0, limit-current-history-reserved) if limit else None,
            "warning": "Hạ tầng thử nghiệm dùng ngân sách lưu trữ chung; hạn mức gói không phải dung lượng ổ đĩa đã cấp riêng." if limit else None}


def ensure_storage_capacity(db, new_bytes):
    from .native_service import StorageError, storage_root
    # Across owners/workers, serialize capacity reservations before their transaction commits.
    if db.get_bind().dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(63891624072)"))
    budget = pool_usage(db)
    if budget["pool_limit_bytes"] and budget["used_bytes"] + budget["reserved_bytes"] + new_bytes > budget["pool_limit_bytes"]:
        raise StorageError(507, "Kho CloudBox thử nghiệm đã hết ngân sách lưu trữ chung. Tệp hiện có vẫn được giữ; hãy liên hệ quản trị viên.")
    root = storage_root()
    root.mkdir(parents=True, exist_ok=True)
    # df inside Docker cannot measure Windows host capacity; the explicit pool limit
    # is the host budget. This additional check protects the guest filesystem too.
    remaining = int(db.query(func.coalesce(func.sum(UploadSession.size-UploadSession.received), 0)).filter(UploadSession.state == "pending", UploadSession.expires_at > utcnow()).scalar())
    if shutil.disk_usage(root).free < new_bytes + remaining + 1024**3:
        raise StorageError(507, "Ổ lưu trữ máy chủ gần đầy. Tạm dừng tải thêm để bảo vệ dữ liệu hiện có.")
