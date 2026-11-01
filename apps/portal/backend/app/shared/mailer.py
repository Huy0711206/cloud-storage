import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

log = logging.getLogger("portal.email")


def send_mail(to: str, subject: str, body: str) -> None:
    """Gửi email qua SMTP. Nếu chưa cấu hình SMTP thì in nội dung ra log (tiện khi phát triển)."""
    if not settings.smtp_host:
        log.warning("SMTP chưa cấu hình. Email gửi tới %s:\n%s\n%s", to, subject, body)
        return
    msg = EmailMessage()
    msg["From"] = settings.mail_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            if settings.smtp_starttls:
                smtp.starttls()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
    except Exception:  # không để lỗi email làm hỏng request
        log.exception("Gửi email tới %s thất bại", to)


def send_verification(to: str, name: str, link: str) -> None:
    send_mail(
        to,
        "Xác thực tài khoản CloudBox",
        f"Xin chào {name},\n\nBấm vào liên kết dưới đây để xác thực email và kích hoạt "
        f"tài khoản lưu trữ của bạn (có hiệu lực 24 giờ):\n\n{link}\n\n"
        "Nếu bạn không đăng ký, hãy bỏ qua email này.\n\nCloudBox",
    )


def send_receipt(to: str, name: str, plan_name: str, months: int, amount: int, expires: str) -> None:
    send_mail(
        to,
        "CloudBox - Xác nhận thanh toán",
        f"Xin chào {name},\n\nChúng tôi đã nhận thanh toán {amount:,} VND cho gói {plan_name} "
        f"({months} tháng).\nGói có hiệu lực đến {expires}.\n\nCảm ơn bạn đã sử dụng CloudBox.".replace(",", "."),
    )
