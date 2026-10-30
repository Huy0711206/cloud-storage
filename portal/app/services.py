"""Nghiệp vụ chính: gói dịch vụ, kích hoạt gói sau thanh toán, đồng bộ quota sang Nextcloud."""
import logging
from datetime import timedelta

from sqlalchemy.orm import Session

from . import nextcloud, vnpay
from .config import settings
from .models import Order, Plan, User, utcnow
from .nextcloud import NextcloudError
from .security import hash_password

log = logging.getLogger("portal.services")

# (mã, tên, dung lượng GB, giá VND / tháng)
DEFAULT_PLANS = [
    ("free", "Miễn phí", 5, 0),
    ("basic", "Cơ bản", 100, 25_000),
    ("standard", "Tiêu chuẩn", 500, 69_000),
    ("premium", "Cao cấp", 2048, 199_000),
]

# số tháng khách mua -> số tháng tính tiền (mua 12 tháng được tặng 2 tháng)
MONTH_CHOICES = {1: 1, 3: 3, 12: 10}


def calc_amount(plan: Plan, months: int) -> int:
    return plan.price_vnd * MONTH_CHOICES[months]


# ---------------------------------------------------------------- khởi tạo dữ liệu
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


def free_plan(db: Session) -> Plan:
    return db.query(Plan).filter(Plan.price_vnd == 0).order_by(Plan.sort).first()


# ---------------------------------------------------------------- Nextcloud
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


# ---------------------------------------------------------------- gói dịch vụ
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


# ---------------------------------------------------------------- thanh toán
def process_payment(db: Session, params: dict) -> tuple[str, str, Order | None, bool]:
    """Xử lý kết quả VNPay (Return URL hoặc IPN). Idempotent: gọi nhiều lần không cộng gói nhiều lần.

    Trả về (RspCode, Message, order, vừa_thanh_toán_xong).
    RspCode theo quy ước IPN của VNPay: 00 thành công, 01 không thấy đơn, 02 đơn đã xác nhận,
    04 sai số tiền, 97 sai chữ ký, 99 lỗi khác.
    """
    if not vnpay.verify_response(params):
        return "97", "Invalid signature", None, False
    order = (db.query(Order).filter_by(txn_ref=params.get("vnp_TxnRef", "")).with_for_update().first())
    if not order:
        return "01", "Order not found", None, False
    try:
        amount_ok = int(params.get("vnp_Amount", "")) == order.amount_vnd * 100
    except ValueError:
        amount_ok = False
    if not amount_ok:
        return "04", "Invalid amount", order, False
    if order.status != "pending":
        return "02", "Order already confirmed", order, False

    success = params.get("vnp_ResponseCode") == "00" and params.get("vnp_TransactionStatus", "00") == "00"
    if not success:
        order.status = "failed"
        db.commit()
        return "00", "Confirm Success", order, False

    order.status = "paid"
    order.paid_at = utcnow()
    order.gateway_txn_no = params.get("vnp_TransactionNo")
    db.commit()
    activate_plan(db, order.user, order.plan, order.months)
    return "00", "Confirm Success", order, True
