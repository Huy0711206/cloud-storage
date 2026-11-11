import logging
from sqlalchemy.orm import Session
from app.core.models import Order, User, utcnow

log = logging.getLogger("portal.services")

from app.features.payments import vnpay
from app.features.billing.service import activate_plan

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
    user = db.query(User).filter_by(id=order.user_id).populate_existing().with_for_update().one()
    activate_plan(db, user, order.plan, order.months, commit=False)
    db.commit()
    return "00", "Confirm Success", order, True

