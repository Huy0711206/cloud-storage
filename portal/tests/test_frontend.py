"""The browser bootstrap must preserve useful state without exposing credentials."""
import json
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from jinja2 import Environment, FileSystemLoader
from app import frontend

def _user():
    plan = SimpleNamespace(id=1, code="free", name="Miễn phí", quota_gb=5,
                           price_vnd=0, is_active=True, sort=0)
    return SimpleNamespace(id=1, email="qa@example.test", full_name="QA </script><script>alert(1)</script>",
                           role="user", is_verified=True, is_active=True, plan_id=1,
                           quota_synced=False, created_at=datetime(2026, 10, 30),
                           plan_expires_at=None, plan=plan, password_hash="private-password-hash")

def test_bootstrap_allowlist_preserves_account_and_orders():
    account = _user()
    order = SimpleNamespace(id=2, months=12, amount_vnd=250000, status="pending",
                            txn_ref="QA-ORDER", gateway_txn_no=None,
                            created_at=datetime(2026, 10, 30), paid_at=None,
                            plan=account.plan, user=account)
    page = frontend.payload("dashboard.html", account,
                            {"orders": [order], "usage": None}, [("error", "Thử lại")],
                            "http://localhost:8080")
    assert page["page"] == "dashboard"
    assert page["user"]["quota_synced"] is False
    assert page["orders"][0]["user"] is None
    assert page["orders"][0]["months"] == 12
    assert page["usage"] is None
    assert page["flashes"] == [("error", "Thử lại")]
    assert page["user"]["created_at"] == "2026-10-30T00:00:00Z"
    encoded = json.dumps(page)
    assert "password_hash" not in encoded
    assert "private-password-hash" not in encoded
    assert set(page["settings"]) == {"nc_public_url"}

def test_template_escapes_script_end_tags():
    env = Environment(loader=FileSystemLoader(Path(__file__).parents[1] / "app" / "templates"))
    page = frontend.payload("dashboard.html", _user(), {}, [], "http://localhost:8080")
    html = env.get_template("app.html").render(page=page, ui_assets={"js":"/static/ui/app.js","css":[]})
    assert "</script><script>alert" not in html
    assert "\\u003c/script\\u003e" in html
    assert 'type="application/json"' in html

def test_manifest_assets_and_missing_build(tmp_path, monkeypatch):
    monkeypatch.setattr(frontend, "STATIC_DIR", tmp_path)
    assert frontend.assets() is None
    (tmp_path / ".vite").mkdir()
    (tmp_path / ".vite" / "manifest.json").write_text(json.dumps({
        "src/main.tsx": {"file":"assets/main-test.js","css":["assets/main-test.css"]}
    }))
    assert frontend.assets() == {"js":"/static/ui/assets/main-test.js","css":["/static/ui/assets/main-test.css"]}
