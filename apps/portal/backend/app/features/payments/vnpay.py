"""Tích hợp cổng thanh toán VNPay (phiên bản API 2.1.0).

Quy tắc ký: sắp xếp tham số vnp_* theo tên (A-Z), nối dạng key=value (value được URL-encode),
rồi tính HMAC-SHA512 bằng HashSecret. Số tiền gửi lên phải nhân 100.
"""
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus

from app.core.config import settings

VN_TZ = timezone(timedelta(hours=7))
_SKIP = ("vnp_SecureHash", "vnp_SecureHashType")


def _encode(params: dict, keep_empty: bool = False) -> str:
    items = sorted(
        (k, v) for k, v in params.items() if keep_empty or (v is not None and str(v) != "")
    )
    return "&".join(f"{k}={quote_plus(str(v))}" for k, v in items)


def sign(params: dict, secret: str, keep_empty: bool = False) -> str:
    return hmac.new(secret.encode(), _encode(params, keep_empty).encode(), hashlib.sha512).hexdigest()


def build_payment_url(*, txn_ref: str, amount_vnd: int, order_info: str, ip_addr: str,
                      return_url: str, expire_minutes: int = 15) -> str:
    now = datetime.now(VN_TZ)
    params = {
        "vnp_Version": "2.1.0",
        "vnp_Command": "pay",
        "vnp_TmnCode": settings.vnpay_tmn_code,
        "vnp_Amount": int(amount_vnd) * 100,
        "vnp_CurrCode": "VND",
        "vnp_TxnRef": txn_ref,
        "vnp_OrderInfo": order_info,
        "vnp_OrderType": "other",
        "vnp_Locale": "vn",
        "vnp_ReturnUrl": return_url,
        "vnp_IpAddr": ip_addr,
        "vnp_CreateDate": now.strftime("%Y%m%d%H%M%S"),
        "vnp_ExpireDate": (now + timedelta(minutes=expire_minutes)).strftime("%Y%m%d%H%M%S"),
    }
    secure_hash = sign(params, settings.vnpay_hash_secret)
    return f"{settings.vnpay_pay_url}?{_encode(params)}&vnp_SecureHash={secure_hash}"


def verify_response(params: dict) -> bool:
    """Kiểm tra chữ ký VNPay trả về (qua Return URL hoặc IPN)."""
    received = (params.get("vnp_SecureHash") or "").lower()
    if not received or not settings.vnpay_hash_secret:
        return False
    data = {k: v for k, v in params.items() if k.startswith("vnp_") and k not in _SKIP}
    # Chấp nhận cả hai cách xử lý tham số rỗng để không bị lệch với phía VNPay.
    for keep_empty in (False, True):
        if hmac.compare_digest(sign(data, settings.vnpay_hash_secret, keep_empty), received):
            return True
    return False
