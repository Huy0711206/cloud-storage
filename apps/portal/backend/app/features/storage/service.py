import logging
from datetime import timedelta
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.models import Order, Plan, User, utcnow
from app.features.storage import client as nextcloud
from app.features.storage.client import NextcloudError
from app.core.security import hash_password

log = logging.getLogger("portal.services")

def provision_nextcloud_account(email: str, password: str, name: str, quota_gb: int) -> None:
    """Tạo tài khoản Nextcloud ở trạng thái bị khóa; chỉ mở khi người dùng xác thực email."""
    nextcloud.nc.create_user(email, password, email, name, quota_gb)
    try:
        nextcloud.nc.disable_user(email)
    except NextcloudError:
        try:  # không để lại tài khoản đang mở mà chưa xác thực
            nextcloud.nc.delete_user(email)
        except NextcloudError:
            log.error("Không thể khóa/xóa tài khoản Nextcloud %s sau khi tạo", email)
        raise



def sync_quota(db: Session, user: User) -> bool:
    """Đặt quota trên Nextcloud đúng theo gói hiện tại. Lỗi thì đánh dấu để thử lại sau."""
    if not user.nc_username or not user.plan_id:
        return True
    plan = db.get(Plan, user.plan_id)
    try:
        nextcloud.nc.set_quota(user.nc_username, plan.quota_gb)
        user.quota_synced = True
    except NextcloudError as exc:
        user.quota_synced = False
        log.error("Đồng bộ quota cho %s thất bại: %s", user.email, exc)
    db.commit()
    return user.quota_synced

