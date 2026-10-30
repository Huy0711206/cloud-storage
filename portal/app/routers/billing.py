import re
import secrets

from fastapi import APIRouter, BackgroundTasks, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from .. import emailer, services, vnpay
from ..config import settings
from ..db import get_db
from ..deps import dt, flash, render, require_user
from ..models import Order, Plan, User

router = APIRouter(prefix="/billing")
IPV4 = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    ip = forwarded or (request.client.host if request.client else "")
    return ip if IPV4.match(ip) else "127.0.0.1"  # VNPay yêu cầu IPv4


def _send_receipt(order: Order) -> None:
    emailer.send_receipt(order.user.email, order.user.full_name, order.plan.name, order.months,
                         order.amount_vnd, dt(order.user.plan_expires_at))


@router.post("/checkout")
def checkout(request: Request, plan_code: str = Form(...), months: int = Form(...),
             db: Session = Depends(get_db), user: User = Depends(require_user)):
    plan = db.query(Plan).filter_by(code=plan_code, is_active=True).first()
    if not plan or plan.price_vnd <= 0 or months not in services.MONTH_CHOICES:
        flash(request, "Gói hoặc thời hạn không hợp lệ.", "error")
        return RedirectResponse("/dashboard", status_code=303)
    if not settings.vnpay_tmn_code or not settings.vnpay_hash_secret:
        flash(request, "Cổng thanh toán VNPay chưa được cấu hình (VNPAY_TMN_CODE / VNPAY_HASH_SECRET).", "error")
        return RedirectResponse("/dashboard", status_code=303)

    order = Order(user_id=user.id, plan_id=plan.id, months=months,
                  amount_vnd=services.calc_amount(plan, months), txn_ref=secrets.token_hex(8).upper())
    db.add(order)
    db.commit()

    url = vnpay.build_payment_url(
        txn_ref=order.txn_ref,
        amount_vnd=order.amount_vnd,
        order_info=f"Thanh toan goi {plan.code} {months} thang don {order.id}",  # không dấu theo khuyến nghị VNPay
        ip_addr=_client_ip(request),
        return_url=f"{settings.base_url}/billing/vnpay/return",
    )
    return RedirectResponse(url, status_code=303)


@router.get("/vnpay/return")
def vnpay_return(request: Request, background: BackgroundTasks, db: Session = Depends(get_db)):
    """Trình duyệt của khách được VNPay chuyển về đây sau khi thanh toán."""
    code, message, order, newly_paid = services.process_payment(db, dict(request.query_params))
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
    code, message, order, newly_paid = services.process_payment(db, dict(request.query_params))
    if newly_paid:
        background.add_task(_send_receipt, order)
    return JSONResponse({"RspCode": code, "Message": message})
