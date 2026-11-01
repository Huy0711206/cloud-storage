import logging
from datetime import timedelta
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.models import Order, Plan, User, utcnow
from app.features.storage import client as nextcloud
from app.features.storage.client import NextcloudError
from app.core.security import hash_password

log = logging.getLogger("portal.services")

from app.features.storage.service import sync_quota

DEFAULT_PLANS = [
    ("free", "Miễn phí", 5, 0),
    ("basic", "Cơ bản", 100, 25_000),
    ("standard", "Tiêu chuẩn", 500, 69_000),
    ("premium", "Cao cấp", 2048, 199_000),
]


MONTH_CHOICES = {1: 1, 3: 3, 12: 10}


def calc_amount(plan: Plan, months: int) -> int:
    return plan.price_vnd * MONTH_CHOICES[months]



def free_plan(db: Session) -> Plan:
    return db.query(Plan).filter(Plan.price_vnd == 0).order_by(Plan.sort).first()



def activate_plan(db: Session, user: User, plan: Plan, months: int) -> None:
    now = utcnow()
    if user.plan_id == plan.id and user.plan_expires_at and user.plan_expires_at > now:
        start = user.plan_expires_at  # gia hạn: cộng nối tiếp vào hạn cũ
    else:
        start = now
    user.plan_id = plan.id
    user.plan_expires_at = start + timedelta(days=settings.plan_days_per_month * months)
    user.quota_synced = False
    db.commit()
    sync_quota(db, user)



def set_free(db: Session, user: User) -> None:
    user.plan_id = free_plan(db).id
    user.plan_expires_at = None
    user.quota_synced = False
    db.commit()
    sync_quota(db, user)



def run_maintenance(db: Session) -> int:
    """Hạ gói các tài khoản hết hạn về Miễn phí và thử đồng bộ lại quota bị lỗi trước đó."""
    now = utcnow()
    expired = db.query(User).filter(User.plan_expires_at.is_not(None), User.plan_expires_at < now).all()
    free = free_plan(db)
    for u in expired:
        u.plan_id = free.id
        u.plan_expires_at = None
        u.quota_synced = False
    db.commit()
    pending = db.query(User).filter(User.quota_synced.is_(False), User.nc_username.is_not(None),
                                    User.is_verified.is_(True)).all()
    for u in pending:
        sync_quota(db, u)
    return len(expired)

