import re
import secrets
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.core.models import Order, Plan, User
from app.shared.http import flash, require_user
from app.features.billing import service as services
from app.features.payments import vnpay

router = APIRouter(prefix='/billing')
IPV4 = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")

def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    ip = forwarded or (request.client.host if request.client else "")
    return ip if IPV4.match(ip) else "127.0.0.1"  # VNPay yêu cầu IPv4


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

