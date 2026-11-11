"""SMTP delivery: never log messages, verification codes, or credentials."""
import logging
import os
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import parseaddr

from app.core.config import settings

log = logging.getLogger("portal.email")


class MailDeliveryError(RuntimeError):
    pass


def delivery_configured() -> bool:
    host = settings.smtp_host.strip().lower()
    development = os.environ.get("MAIL_DELIVERY_MODE", "production").lower() == "development"
    if not host:
        return False
    if not development and host in {"mailpit", "localhost", "127.0.0.1", "::1"}:
        return False
    if not development and not (settings.smtp_starttls or settings.smtp_port == 465):
        return False
    return bool(parseaddr(settings.mail_from)[1] and (development or settings.smtp_user))


def send_mail(to: str, subject: str, body: str) -> None:
    if not delivery_configured():
        raise MailDeliveryError("Cấu hình gửi email chưa sẵn sàng.")
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = settings.mail_from, to, subject
    msg.set_content(body)
    try:
        connection = smtplib.SMTP_SSL if settings.smtp_port == 465 else smtplib.SMTP
        kwargs = {"timeout": 12}
        if settings.smtp_port == 465:
            kwargs["context"] = ssl.create_default_context()
        with connection(settings.smtp_host, settings.smtp_port, **kwargs) as smtp:
            if settings.smtp_starttls and settings.smtp_port != 465:
                smtp.starttls(context=ssl.create_default_context())
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            refused = smtp.send_message(msg)
            if refused:
                raise MailDeliveryError("Máy chủ email từ chối người nhận.")
    except Exception:
        # Server exception strings may contain identifiers or parts of a message.
        log.warning("Email delivery failed; check SMTP configuration locally.")
        raise MailDeliveryError("Chưa gửi được email. Hãy thử lại sau.") from None


def send_verification_code(to: str, name: str, code: str) -> None:
    send_mail(to, "Mã xác minh tài khoản CloudBox",
              f"Xin chào {name},\n\nMã xác minh CloudBox của bạn là: {code}\n\n"
              "Mã có hiệu lực 10 phút và chỉ dùng một lần. Không chia sẻ mã này.\n"
              "Nếu bạn không đăng ký, hãy bỏ qua email này.\n\nCloudBox")


def send_password_reset(to: str, name: str, link: str) -> None:
    send_mail(to, "Đặt lại mật khẩu CloudBox",
              f"Xin chào {name},\n\nDùng liên kết sau để đặt lại mật khẩu CloudBox (30 phút):\n"
              f"{link}\n\nLiên kết chỉ dùng một lần. Nếu bạn không yêu cầu, hãy bỏ qua.\nCloudBox")


def send_receipt(to: str, name: str, plan_name: str, months: int, amount: int, expires: str) -> bool:
    try:
        send_mail(to, "CloudBox - Xác nhận thanh toán",
                  f"Xin chào {name},\n\nChúng tôi đã nhận thanh toán {amount:,} VND cho gói {plan_name} "
                  f"({months} tháng).\nGói có hiệu lực đến {expires}.\n\nCloudBox".replace(",", "."))
        return True
    except MailDeliveryError:
        # Receipt delivery must not roll back a confirmed payment or claim delivery.
        log.warning("Payment confirmed but receipt email could not be delivered.")
        return False
