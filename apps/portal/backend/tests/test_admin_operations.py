"""Readiness and audit checks use disposable SQLite and storage directories."""
import json
import re
from datetime import timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.database import Base
from app.core.models import Order, Plan, User, utcnow
from app.features.administration import health, routes
from app.features.administration.audit import AdminAuditEntry
from app.shared import frontend
from test_native_business import ADMIN_EMAIL, business, login


@pytest.fixture
def admin_session(business, monkeypatch):
    client, sessions, _ = business
    monkeypatch.setattr(frontend, "assets", lambda: {"js": "/static/ui/test.js", "css": []})
    assert login(client, ADMIN_EMAIL).status_code == 303
    with sessions() as db:
        admin = db.query(User).filter_by(email=ADMIN_EMAIL).one()
        customer = db.query(User).filter_by(role="user").order_by(User.id).first()
        basic = db.query(Plan).filter_by(code="basic").one()
        yield client, sessions, admin.id, customer.id, basic.id


def bootstrap(response):
    assert response.status_code == 200, response.text
    data = re.search(r'<script id="cloudbox-data" type="application/json">(.*?)</script>', response.text, re.S)
    return json.loads(data.group(1))


def change_price(client, plan_id, price=42_000, quota_gb=100):
    return client.post(f"/admin/plans/{plan_id}",
                       data={"name": "Cơ bản", "quota_gb": quota_gb, "price_vnd": price, "is_active": "1"})


def test_paid_count_matches_billing_at_expiry_boundary(admin_session, monkeypatch):
    client, sessions, admin_id, customer_id, plan_id = admin_session
    now = utcnow()
    monkeypatch.setattr(routes, "utcnow", lambda: now)
    with sessions() as db:
        customer = db.get(User, customer_id)
        customer.plan_id = plan_id
        customer.plan_expires_at = now + timedelta(seconds=1)
        admin = db.get(User, admin_id)
        admin.plan_id = plan_id
        admin.plan_expires_at = customer.plan_expires_at
        free = db.query(User).filter(User.role == "user", User.id != customer_id).one()
        free.plan_expires_at = customer.plan_expires_at
        db.commit()
    assert bootstrap(client.get("/admin"))["stats"]["paid_users"] == 1
    for expires in (now, now - timedelta(seconds=1)):
        with sessions() as db:
            db.get(User, customer_id).plan_expires_at = expires
            db.commit()
        assert bootstrap(client.get("/admin"))["stats"]["paid_users"] == 0


def test_readiness_reports_only_generic_status(admin_session, tmp_path, monkeypatch):
    client, _, _, _, _ = admin_session
    root = tmp_path / "blobs"
    assert client.get("/healthz").json() == {"status": "ok"}
    response = client.get("/readyz")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
    assert not root.exists()

    root.mkdir()
    gib = health.MIN_FREE_BYTES
    monkeypatch.setattr(health.shutil, "disk_usage", lambda path: SimpleNamespace(total=20 * gib, free=gib))
    response = client.get("/readyz")
    assert response.status_code == 200 and response.json() == {"status": "ok"}

    def disconnected(*args, **kwargs):
        raise OperationalError("SELECT 1", {}, Exception("private database detail"))

    monkeypatch.setattr(Session, "execute", disconnected)
    response = client.get("/readyz")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}


def test_diagnostics_distinguishes_budget_disk_and_unavailable_data(admin_session, tmp_path, monkeypatch):
    client, _, _, _, _ = admin_session
    (tmp_path / "blobs").mkdir()
    gib = health.MIN_FREE_BYTES
    usage = {"total": 40 * gib, "free": 20 * gib}
    pool = {"pool_limit_bytes": 20, "used_bytes": 2, "reserved_bytes": 1, "available_bytes": 17}
    monkeypatch.setattr(health.shutil, "disk_usage", lambda path: SimpleNamespace(**usage))
    monkeypatch.setattr(health, "pool_usage", lambda db: pool)

    report = client.get("/admin/diagnostics").json()
    assert report["database"] == report["storage"]["status"] == report["budget"]["status"] == "ok"
    assert report["budget"]["reserved_bytes"] == 1 and report["storage"]["free_bytes"] == 20 * gib

    usage["free"], pool["available_bytes"] = 4 * gib, 4
    report = client.get("/admin/diagnostics").json()
    assert report["storage"]["status"] == report["budget"]["status"] == "low"

    usage["free"], pool["available_bytes"] = gib, 0
    report = client.get("/admin/diagnostics").json()
    assert report["storage"]["status"] == "critical"
    assert report["budget"]["status"] == "full"

    def cannot_read(*args):
        raise PermissionError("private storage path")

    def invalid_pool(*args):
        raise ValueError("private configuration")

    monkeypatch.setattr(health.shutil, "disk_usage", cannot_read)
    monkeypatch.setattr(health, "pool_usage", invalid_pool)
    report = client.get("/admin/diagnostics").json()
    assert report == {"database": "ok", "storage": {"status": "unavailable"}, "budget": {"status": "unavailable"}}


def test_operations_pages_require_administrator(business):
    client, _, _ = business
    for path in ("/admin/audit", "/admin/diagnostics"):
        assert client.get(path).status_code == 303
    assert login(client).status_code == 303
    for path in ("/admin/audit", "/admin/diagnostics"):
        assert client.get(path).status_code == 403


def test_audit_tracks_lock_grant_and_price(admin_session):
    client, sessions, actor_id, customer_id, plan_id = admin_session
    for _ in range(2):
        assert client.post(f"/admin/users/{customer_id}/toggle").status_code == 303
    for code in ("basic", "free"):
        assert client.post(f"/admin/users/{customer_id}/grant", data={"plan_code": code, "months": 1}).status_code == 303
    assert change_price(client, plan_id).status_code == 303
    assert change_price(client, plan_id, quota_gb=101).status_code == 303
    assert change_price(client, plan_id, price=-1).status_code == 303

    with sessions() as db:
        entries = db.query(AdminAuditEntry).order_by(AdminAuditEntry.id).all()
        assert [r.action for r in entries] == ["account_lock", "account_lock", "plan_grant", "plan_grant", "plan_price"]
        assert {r.actor_id for r in entries} == {actor_id}
        assert [r.subject_id for r in entries] == [customer_id] * 4 + [plan_id]
        assert entries[0].before == entries[1].after == {"is_active": True}
        assert entries[0].after == entries[1].before == {"is_active": False}
        assert entries[2].before == entries[3].after == {"plan_code": "free", "expires_at": None}
        assert entries[2].after == entries[3].before
        assert entries[2].after["plan_code"] == "basic" and entries[2].after["expires_at"]
        assert entries[4].before == {"price_vnd": 39_000} and entries[4].after == {"price_vnd": 42_000}

    entries_json = bootstrap(client.get("/admin/audit"))["audit"]["entries"]
    assert [r["action"] for r in entries_json] == [
        "Đổi giá gói", "Cấp gói", "Cấp gói", "Mở khóa tài khoản", "Khóa tài khoản"
    ]
    assert bootstrap(client.get("/admin"))["audit"] is None


def test_audit_paginates_newest_first(admin_session):
    client, sessions, actor_id, customer_id, _ = admin_session
    now = utcnow()
    with sessions() as db:
        for _ in range(27):
            db.add(AdminAuditEntry(created_at=now, actor_id=actor_id, action="account_lock", subject_id=customer_id,
                                   before={"is_active": True}, after={"is_active": False}))
        db.commit()
    first = bootstrap(client.get("/admin/audit"))["audit"]
    second = bootstrap(client.get("/admin/audit?page=2"))["audit"]
    assert first["pages"] == second["pages"] == 2
    assert first["page"] == 1 and second["page"] == 2
    assert [r["id"] for r in first["entries"]] == list(range(27, 2, -1))
    assert [r["id"] for r in second["entries"]] == [2, 1]


@pytest.mark.parametrize("action", ["toggle", "grant_paid", "grant_free", "price"])
def test_audit_failure_rolls_back_business_action(admin_session, action):
    client, sessions, _, customer_id, plan_id = admin_session
    with sessions() as db:
        customer = db.get(User, customer_id)
        if action == "grant_free":
            customer.plan_id = plan_id
            customer.plan_expires_at = utcnow() + timedelta(days=30)
            db.commit()
        original = (customer.is_active, customer.plan_id, customer.plan_expires_at, customer.quota_synced)

    def reject_audit(session, *args):
        if any(isinstance(row, AdminAuditEntry) for row in session.new):
            raise RuntimeError("prescribed audit write failure")

    event.listen(sessions, "before_flush", reject_audit)
    try:
        with pytest.raises(RuntimeError, match="prescribed audit write failure"):
            if action == "toggle":
                client.post(f"/admin/users/{customer_id}/toggle")
            elif action == "price":
                change_price(client, plan_id)
            else:
                client.post(f"/admin/users/{customer_id}/grant",
                            data={"plan_code": "free" if action == "grant_free" else "basic", "months": 1})
    finally:
        event.remove(sessions, "before_flush", reject_audit)
    with sessions() as db:
        customer = db.get(User, customer_id)
        assert (customer.is_active, customer.plan_id, customer.plan_expires_at, customer.quota_synced) == original
        assert db.get(Plan, plan_id).price_vnd == 39_000
        assert db.query(AdminAuditEntry).count() == 0


def test_audit_table_creation_preserves_existing_rows(tmp_path):
    engine = create_engine("sqlite:///" + str(tmp_path / "existing.db"))
    Base.metadata.create_all(engine, tables=[Plan.__table__, User.__table__, Order.__table__])
    with Session(engine) as db:
        db.add(Plan(id=31, code="existing", name="Existing", quota_gb=17, price_vnd=32_000))
        db.add(User(id=89, email="existing@example.test", full_name="Existing", password_hash="fixture-hash", plan_id=31))
        db.add(Order(id=9, user_id=89, plan_id=31, months=1, amount_vnd=32_000, status="paid", txn_ref="fixture-order"))
        db.commit()
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        assert db.get(User, 89).password_hash == "fixture-hash"
        assert db.get(User, 89).plan_id == 31 and db.get(Plan, 31).price_vnd == 32_000
        assert db.get(Order, 9).txn_ref == "fixture-order"
        assert db.query(AdminAuditEntry).count() == 0
    engine.dispose()
