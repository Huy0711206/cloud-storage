"""Isolated browser QA fixture. Run from portal/tests, never from production app code.

The fixture unconditionally selects a new temporary SQLite database before importing
the application. It replaces Nextcloud and email delivery with in-memory fakes.
It is not copied into either production Docker image.
"""
import os
from pathlib import Path
import sys
import tempfile
from datetime import timedelta

PORTAL_ROOT = Path(__file__).resolve().parents[1]
if (PORTAL_ROOT / "app").is_dir():
    sys.path.insert(0, str(PORTAL_ROOT))

QA_DIRECTORY = Path(tempfile.mkdtemp(prefix="cloudbox-design-qa-"))
os.environ.update(
    DATABASE_URL="sqlite:///" + str(QA_DIRECTORY / "browser.db"),
    SECRET_KEY="cloudbox-design-qa-only-not-production",
    BASE_URL="http://localhost:8001",
    NEXTCLOUD_URL="http://invalid-qa-nextcloud",
    NEXTCLOUD_PUBLIC_URL="http://localhost:8080",
    NEXTCLOUD_ADMIN_USER="qa-only",
    NEXTCLOUD_ADMIN_PASSWORD="qa-only",
    ADMIN_EMAIL="admin@cloudbox.test",
    ADMIN_PASSWORD="PreviewAdmin123",
    SMTP_HOST="",
    SMTP_USER="",
    SMTP_PASSWORD="",
    MAIL_FROM="CloudBox QA <qa@cloudbox.test>",
    VNPAY_TMN_CODE="QA-ONLY",
    VNPAY_HASH_SECRET="qa-signature-only-no-real-merchant",
    VNPAY_PAY_URL="https://sandbox.vnpayment.vn/paymentv2/vpcpay.html",
)

from app import emailer, nextcloud, services  # noqa: E402
from app.config import settings  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.models import Order, Plan, User, utcnow  # noqa: E402
from app.nextcloud import NextcloudError  # noqa: E402
from app.security import hash_password  # noqa: E402

assert settings.database_url.startswith("sqlite:///"), "Browser QA must never use PostgreSQL"
assert str(QA_DIRECTORY) in settings.database_url, "Browser QA must use its new temporary directory"


class FakeStorage:
    def __init__(self):
        self.users = {}
        self.fail_usage = False

    def create_user(self, userid, password, email, display_name, quota_gb):
        if userid in self.users:
            raise NextcloudError("QA account already exists", code=102)
        self.users[userid] = {"password": password, "quota": quota_gb, "enabled": True}

    def disable_user(self, userid):
        self.users[userid]["enabled"] = False

    def enable_user(self, userid):
        self.users[userid]["enabled"] = True

    def delete_user(self, userid):
        self.users.pop(userid, None)

    def set_password(self, userid, password):
        self.users[userid]["password"] = password

    def set_quota(self, userid, quota_gb):
        self.users[userid]["quota"] = quota_gb

    def get_usage(self, userid):
        if self.fail_usage:
            raise NextcloudError("QA simulated storage outage")
        return int(1.24 * 1024**3), self.users[userid]["quota"] * 1024**3


fake_storage = FakeStorage()
nextcloud.nc = fake_storage
emailer.send_verification = lambda *args, **kwargs: None
emailer.send_receipt = lambda *args, **kwargs: None

Base.metadata.create_all(engine)
with SessionLocal() as db:
    services.seed(db)
    free = services.free_plan(db)
    basic = db.query(Plan).filter_by(code="basic").one()
    standard = db.query(Plan).filter_by(code="standard").one()
    user = User(
        email="demo@cloudbox.test",
        full_name="Minh Anh",
        password_hash=hash_password("PreviewUser123"),
        role="user",
        is_verified=True,
        is_active=True,
        nc_username="demo@cloudbox.test",
        plan_id=free.id,
        created_at=utcnow() - timedelta(days=90),
    )
    db.add(user)
    db.flush()
    fake_storage.create_user(user.email, "PreviewUser123", user.email, user.full_name, free.quota_gb)
    # A historical, expired paid month; the account is now on the free plan.
    db.add(Order(
        user_id=user.id, plan_id=basic.id, months=1,
        amount_vnd=basic.price_vnd, status="paid", txn_ref="QA-PAID-001",
        gateway_txn_no="QA-ONLY-001", created_at=utcnow() - timedelta(days=65),
        paid_at=utcnow() - timedelta(days=65),
    ))
    db.add(Order(
        user_id=user.id, plan_id=standard.id, months=12,
        amount_vnd=standard.price_vnd * 10, status="pending", txn_ref="QA-PENDING-002",
        created_at=utcnow() - timedelta(hours=1),
    ))
    db.commit()

from app.main import app  # noqa: E402


@app.post("/__qa/usage-error", include_in_schema=False)
def qa_usage_error(enabled: bool = True):
    fake_storage.fail_usage = enabled
    return {"enabled": fake_storage.fail_usage}


@app.get("/__qa/state", include_in_schema=False)
def qa_state():
    with SessionLocal() as db:
        return {
            "users": db.query(User).count(),
            "plans": db.query(Plan).count(),
            "orders": db.query(Order).count(),
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
