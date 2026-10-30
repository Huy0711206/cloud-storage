"""Kiểm thử toàn bộ luồng: đăng ký -> xác thực email -> đăng nhập -> thanh toán VNPay -> quota Nextcloud -> admin.

Nextcloud được thay bằng bản giả (FakeNC) nên test chạy được mà không cần Docker.
Chạy:  cd portal && pip install -r requirements.txt pytest && pytest -q
"""
import os
import tempfile
from datetime import timedelta
from urllib.parse import parse_qsl, urlparse

import pytest

_tmp = tempfile.mkdtemp()
os.environ.update(
    DATABASE_URL=f"sqlite:///{_tmp}/test.db",
    SECRET_KEY="test-secret",
    BASE_URL="http://testserver",
    ADMIN_EMAIL="admin@example.com",
    ADMIN_PASSWORD="Admin-Pass-12345",
    VNPAY_TMN_CODE="TESTCODE",
    VNPAY_HASH_SECRET="TESTSECRET",
    VNPAY_PAY_URL="https://sandbox.vnpayment.vn/paymentv2/vpcpay.html",
    SMTP_HOST="",
)

from fastapi.testclient import TestClient  # noqa: E402

from app import emailer, nextcloud, services, vnpay  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Order, User, utcnow  # noqa: E402
from app.nextcloud import NextcloudError  # noqa: E402


class FakeNC:
    def __init__(self):
        self.users, self.fail_quota = {}, False

    def create_user(self, userid, password, email, display_name, quota_gb):
        if userid in self.users:
            raise NextcloudError("User already exists", code=102)
        self.users[userid] = dict(password=password, quota=quota_gb, enabled=True)

    def disable_user(self, userid): self.users[userid]["enabled"] = False
    def enable_user(self, userid): self.users[userid]["enabled"] = True
    def delete_user(self, userid): self.users.pop(userid, None)
    def set_password(self, userid, password): self.users[userid]["password"] = password

    def set_quota(self, userid, quota_gb):
        if self.fail_quota:
            raise NextcloudError("down")
        self.users[userid]["quota"] = quota_gb

    def get_usage(self, userid): return 1024**3, self.users[userid]["quota"] * 1024**3


@pytest.fixture(scope="module")
def env():
    fake = FakeNC()
    nextcloud.nc = fake
    sent = {"verify": [], "receipt": []}
    emailer.send_verification = lambda to, name, link: sent["verify"].append((to, link))
    emailer.send_receipt = lambda *a, **k: sent["receipt"].append(a)
    with TestClient(app) as client:
        yield client, fake, sent


EMAIL, PASSWORD = "sv@example.com", "MatKhau12345"


def _register(client, email=EMAIL, password=PASSWORD):
    return client.post("/register", data=dict(full_name="Sinh Vien", email=email, password=password, password2=password))


def _signed_callback(order, code="00", amount=None):
    p = {
        "vnp_Amount": str(amount if amount is not None else order.amount_vnd * 100),
        "vnp_BankCode": "NCB", "vnp_ResponseCode": code, "vnp_TmnCode": "TESTCODE",
        "vnp_TransactionNo": "14000001", "vnp_TransactionStatus": code, "vnp_TxnRef": order.txn_ref,
        "vnp_OrderInfo": "Thanh toan", "vnp_PayDate": "20261028170000",
    }
    p["vnp_SecureHash"] = vnpay.sign(p, "TESTSECRET")
    return p


def _order(email=EMAIL):
    with SessionLocal() as db:
        return db.query(Order).join(User).filter(User.email == email).order_by(Order.id.desc()).first()


def test_seed_plans_and_admin(env):
    with SessionLocal() as db:
        assert [p.code for p in db.query(services.Plan).order_by(services.Plan.sort)] == ["free", "basic", "standard", "premium"]
        assert db.query(User).filter_by(email="admin@example.com", role="admin").one().is_verified


def test_register_creates_locked_nextcloud_account(env):
    client, fake, sent = env
    assert _register(client).status_code == 200
    acct = fake.users[EMAIL]
    assert acct["enabled"] is False and acct["quota"] == 5 and acct["password"] == PASSWORD
    assert sent["verify"] and sent["verify"][-1][0] == EMAIL


def test_register_validation(env):
    client, *_ = env
    assert _register(client, email="x@example.com", password="short1").status_code == 400
    assert _register(client, email="x@example.com", password="onlyletterslong").status_code == 400
    assert _register(client).status_code == 400  # trùng email


def test_login_blocked_until_verified_then_ok(env):
    client, fake, sent = env
    r = client.post("/login", data=dict(email=EMAIL, password=PASSWORD))
    assert r.status_code == 400 and "chưa xác thực" in r.text

    assert client.get("/verify?token=bad").status_code == 400
    link = sent["verify"][-1][1]
    assert client.get(link.replace("http://testserver", "")).status_code == 200
    assert fake.users[EMAIL]["enabled"] is True

    assert client.post("/login", data=dict(email=EMAIL, password="sai-mat-khau-1")).status_code == 400
    r = client.post("/login", data=dict(email=EMAIL, password=PASSWORD), follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/dashboard"
    page = client.get("/dashboard")
    assert page.status_code == 200 and "Miễn phí" in page.text


def test_vnpay_signature_matches_manual_hmac():
    import hashlib, hmac
    params = {"vnp_B": "2", "vnp_A": "x y", "vnp_C": ""}
    expected = hmac.new(b"k", b"vnp_A=x+y&vnp_B=2", hashlib.sha512).hexdigest()
    assert vnpay.sign(params, "k") == expected


def test_checkout_redirects_to_signed_vnpay_url(env):
    client, *_ = env
    r = client.post("/billing/checkout", data=dict(plan_code="basic", months=1), follow_redirects=False)
    assert r.status_code == 303
    url = urlparse(r.headers["location"])
    assert url.netloc == "sandbox.vnpayment.vn"
    q = dict(parse_qsl(url.query))
    assert q["vnp_Amount"] == str(25_000 * 100) and q["vnp_TmnCode"] == "TESTCODE"
    assert vnpay.verify_response(q)  # chữ ký do chính ta tạo phải hợp lệ
    assert _order().status == "pending"


def test_checkout_rejects_free_plan_and_bad_months(env):
    client, *_ = env
    for data in (dict(plan_code="free", months=1), dict(plan_code="basic", months=7), dict(plan_code="nope", months=1)):
        r = client.post("/billing/checkout", data=data, follow_redirects=False)
        assert r.status_code == 303 and r.headers["location"] == "/dashboard"


def test_payment_return_rejects_bad_signature_and_wrong_amount(env):
    client, fake, _ = env
    order = _order()
    p = _signed_callback(order)
    p["vnp_Amount"] = "100"  # bị sửa sau khi ký
    assert client.get("/billing/vnpay/return", params=p).status_code == 400
    r = client.get("/billing/vnpay/return", params=_signed_callback(order, amount=100))
    assert r.status_code == 400
    assert _order().status == "pending" and fake.users[EMAIL]["quota"] == 5


def test_payment_success_upgrades_quota_once(env):
    client, fake, sent = env
    order = _order()
    params = _signed_callback(order)
    r = client.get("/billing/vnpay/return", params=params)
    assert r.status_code == 200 and "Thanh toán thành công" in r.text
    assert fake.users[EMAIL]["quota"] == 100
    paid = _order()
    assert paid.status == "paid" and paid.gateway_txn_no == "14000001"
    with SessionLocal() as db:
        u = db.query(User).filter_by(email=EMAIL).one()
        first_expiry = u.plan_expires_at
        assert u.plan.code == "basic" and first_expiry > utcnow() + timedelta(days=29)
    assert len(sent["receipt"]) == 1

    # IPN gọi lại sau Return URL: không cộng gói lần hai
    ipn = client.get("/billing/vnpay/ipn", params=params).json()
    assert ipn["RspCode"] == "02"
    with SessionLocal() as db:
        assert db.query(User).filter_by(email=EMAIL).one().plan_expires_at == first_expiry


def test_ipn_unknown_order_and_failed_payment(env):
    client, fake, _ = env
    ghost = Order(txn_ref="NOSUCHORDER", amount_vnd=25000)
    assert client.get("/billing/vnpay/ipn", params=_signed_callback(ghost)).json()["RspCode"] == "01"

    client.post("/billing/checkout", data=dict(plan_code="standard", months=1))
    order = _order()
    assert client.get("/billing/vnpay/ipn", params=_signed_callback(order, code="24")).json()["RspCode"] == "00"
    assert _order().status == "failed" and fake.users[EMAIL]["quota"] == 100


def test_renewal_extends_from_existing_expiry(env):
    client, fake, _ = env
    with SessionLocal() as db:
        before = db.query(User).filter_by(email=EMAIL).one().plan_expires_at
    client.post("/billing/checkout", data=dict(plan_code="basic", months=3))
    client.get("/billing/vnpay/return", params=_signed_callback(_order()))
    with SessionLocal() as db:
        after = db.query(User).filter_by(email=EMAIL).one().plan_expires_at
    assert after == before + timedelta(days=90)


def test_nextcloud_outage_during_payment_is_recovered_by_maintenance(env):
    client, fake, _ = env
    client.post("/billing/checkout", data=dict(plan_code="premium", months=1))
    order = _order()
    fake.fail_quota = True
    r = client.get("/billing/vnpay/return", params=_signed_callback(order))
    assert "Thanh toán thành công" in r.text  # tiền đã nhận, không mất đơn
    assert fake.users[EMAIL]["quota"] == 100
    with SessionLocal() as db:
        assert db.query(User).filter_by(email=EMAIL).one().quota_synced is False
    fake.fail_quota = False
    with SessionLocal() as db:
        services.run_maintenance(db)
    assert fake.users[EMAIL]["quota"] == 2048


def test_expired_plan_falls_back_to_free(env):
    _, fake, _ = env
    with SessionLocal() as db:
        u = db.query(User).filter_by(email=EMAIL).one()
        u.plan_expires_at = utcnow() - timedelta(days=1)
        db.commit()
        assert services.run_maintenance(db) == 1
        db.refresh(u)
        assert u.plan.code == "free" and u.plan_expires_at is None
    assert fake.users[EMAIL]["quota"] == 5


def test_user_cannot_access_admin_but_admin_can(env):
    client, fake, _ = env
    assert client.get("/admin").status_code == 403
    assert client.post("/admin/maintenance").status_code == 403

    admin = TestClient(app)
    r = admin.post("/login", data=dict(email="admin@example.com", password="Admin-Pass-12345"), follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/admin"
    for path in ("/admin", "/admin/users", "/admin/orders", "/admin/plans"):
        assert admin.get(path).status_code == 200

    with SessionLocal() as db:
        uid = db.query(User).filter_by(email=EMAIL).one().id
    admin.post(f"/admin/users/{uid}/toggle")
    assert fake.users[EMAIL]["enabled"] is False
    assert client.post("/login", data=dict(email=EMAIL, password=PASSWORD)).status_code == 400
    admin.post(f"/admin/users/{uid}/toggle")
    assert fake.users[EMAIL]["enabled"] is True

    admin.post(f"/admin/users/{uid}/grant", data=dict(plan_code="standard", months=1))
    assert fake.users[EMAIL]["quota"] == 500


def test_admin_plan_quota_change_propagates(env):
    _, fake, _ = env
    admin = TestClient(app)
    admin.post("/login", data=dict(email="admin@example.com", password="Admin-Pass-12345"))
    with SessionLocal() as db:
        plan = db.query(services.Plan).filter_by(code="standard").one()
    admin.post(f"/admin/plans/{plan.id}", data=dict(name="Tiêu chuẩn", quota_gb=600, price_vnd=69000, is_active="1"))
    assert fake.users[EMAIL]["quota"] == 600


def test_change_password_syncs_to_nextcloud(env):
    client, fake, _ = env
    client.post("/login", data=dict(email=EMAIL, password=PASSWORD))
    client.post("/account/password", data=dict(current=PASSWORD, new="MatKhauMoi123", new2="MatKhauMoi123"))
    assert fake.users[EMAIL]["password"] == "MatKhauMoi123"
