import logging
from datetime import timedelta
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.models import Order, Plan, User, utcnow
from app.features.storage import client as nextcloud
from app.features.storage.client import NextcloudError
from app.core.security import hash_password

log = logging.getLogger("portal.services")

from app.features.billing.service import DEFAULT_PLANS

def seed(db: Session) -> None:
    if db.query(Plan).count() == 0:
        for i, (code, name, gb, price) in enumerate(DEFAULT_PLANS):
            db.add(Plan(code=code, name=name, quota_gb=gb, price_vnd=price, sort=i))
        db.commit()
    if settings.admin_email and settings.admin_password:
        if not db.query(User).filter_by(email=settings.admin_email).first():
            db.add(User(email=settings.admin_email, full_name="Quản trị viên",
                        password_hash=hash_password(settings.admin_password),
                        role="admin", is_verified=True))
            db.commit()
            log.info("Đã tạo tài khoản admin %s", settings.admin_email)
    else:
        log.warning("ADMIN_EMAIL / ADMIN_PASSWORD chưa đặt: chưa có tài khoản admin.")

