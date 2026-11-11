import os


class Settings:
    """Đọc toàn bộ cấu hình từ biến môi trường (xem .env.example)."""

    def __init__(self) -> None:
        e = os.environ.get
        self.database_url = e("DATABASE_URL", "sqlite:///./portal.db")
        self.secret_key = e("SECRET_KEY", "dev-secret-change-me")
        self.base_url = e("BASE_URL", "http://localhost:8000").rstrip("/")

        self.nc_public_url = "/dashboard#storage"  # compatibility key; no external storage URL

        self.admin_email = (e("ADMIN_EMAIL", "") or "").strip().lower()
        self.admin_password = e("ADMIN_PASSWORD", "")

        self.smtp_host = e("SMTP_HOST", "")
        self.smtp_port = int(e("SMTP_PORT", "587") or 587)
        self.smtp_user = e("SMTP_USER", "")
        self.smtp_password = e("SMTP_PASSWORD", "")
        self.smtp_starttls = (e("SMTP_STARTTLS", "false") or "").lower() in ("1", "true", "yes")
        self.mail_from = e("MAIL_FROM", "CloudBox <no-reply@cloudbox.local>")

        self.vnpay_tmn_code = e("VNPAY_TMN_CODE", "")
        self.vnpay_hash_secret = e("VNPAY_HASH_SECRET", "")
        self.vnpay_pay_url = e("VNPAY_PAY_URL", "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html")

        self.plan_days_per_month = 30


settings = Settings()
