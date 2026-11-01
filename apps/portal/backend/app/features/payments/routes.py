import re
import secrets
from fastapi import APIRouter, BackgroundTasks, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.core.models import Order, Plan, User
from app.core.security import hash_password, make_verify_token, read_verify_token, verify_password
from app.shared import mailer as emailer
from app.shared.http import current_user, dt, flash, render, require_user, require_admin
from app.features.storage import client as nextcloud
from app.features.storage.client import NextcloudError
from app.features.billing import service as services
from app.features.storage import service as storage_services
from app.features.payments import service as payment_services
from app.features.payments import vnpay

router = APIRouter(prefix='/billing')

def _send_receipt(order: Order) -> None:
    emailer.send_receipt(order.user.email, order.user.full_name, order.plan.name, order.months,
                         order.amount_vnd, dt(order.user.plan_expires_at))



@router.get("/vnpay/return")
def vnpay_return(request: Request, background: BackgroundTasks, db: Session = Depends(get_db)):
    """Trình duyệt của khách được VNPay chuyển về đây sau khi thanh toán."""
    code, message, order, newly_paid = payment_services.process_payment(db, dict(request.query_params))
    if newly_paid:
        background.add_task(_send_receipt, order)

    if code == "97":
        return render(request, "message.html", None, status_code=400, title="Không xác minh được giao dịch",
                      text="Chữ ký giao dịch không hợp lệ.", kind="error")
    if order is None or code in ("01", "04"):
        return render(request, "message.html", None, status_code=400, title="Giao dịch không hợp lệ",
                      text="Không tìm thấy đơn hàng khớp với giao dịch này.", kind="error")
    if order.status == "paid":
        return render(request, "message.html", None, title="Thanh toán thành công",
                      text=f"Gói {order.plan.name} ({order.months} tháng) đã được kích hoạt. "
                           f"Dung lượng mới sẽ có hiệu lực ngay trong kho lưu trữ của bạn.",
                      kind="ok", link=("/dashboard", "Về trang của tôi"))
    return render(request, "message.html", None, title="Thanh toán chưa hoàn tất",
                  text="Giao dịch đã bị hủy hoặc không thành công. Bạn chưa bị trừ tiền.", kind="error",
                  link=("/dashboard", "Thử lại"))



@router.get("/vnpay/ipn")
def vnpay_ipn(request: Request, background: BackgroundTasks, db: Session = Depends(get_db)):
    """VNPay gọi máy chủ-tới-máy chủ để xác nhận kết quả. Cần địa chỉ công khai (ví dụ qua ngrok)."""
    code, message, order, newly_paid = payment_services.process_payment(db, dict(request.query_params))
    if newly_paid:
        background.add_task(_send_receipt, order)
    return JSONResponse({"RspCode": code, "Message": message})

