"""Public UI bootstrap. Only explicitly allow-listed fields reach the browser."""
import json
from pathlib import Path

STATIC_DIR = Path(__file__).resolve().parents[1] / "static" / "ui"

def assets():
    manifest_path = STATIC_DIR / ".vite" / "manifest.json"
    if not manifest_path.is_file():
        return None
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entry = manifest.get("src/main.tsx")
    if not entry:
        return None
    return {"js": "/static/ui/" + entry["file"],
            "css": ["/static/ui/" + path for path in entry.get("css", [])]}

def _dt(value):
    return value.isoformat() + "Z" if value else None

def plan(p):
    if p is None:
        return None
    return {key: getattr(p, key) for key in ("id", "code", "name", "quota_gb", "price_vnd", "is_active", "sort")}

def user(u):
    if u is None:
        return None
    return {
        **{key: getattr(u, key) for key in ("id", "email", "full_name", "role", "is_verified",
                                           "is_active", "plan_id", "quota_synced")},
        "created_at": _dt(u.created_at), "plan_expires_at": _dt(u.plan_expires_at),
        "plan": plan(u.plan),
    }

def order(o, include_user=False):
    return {
        **{key: getattr(o, key) for key in ("id", "months", "amount_vnd", "status", "txn_ref", "gateway_txn_no")},
        "created_at": _dt(o.created_at), "paid_at": _dt(o.paid_at),
        "plan": plan(o.plan), "user": user(o.user) if include_user else None,
    }

def payload(name, current, ctx, flashes, nc_public_url):
    page = name.removesuffix(".html")
    admin = bool(current and current.role == "admin")
    return {
        "page": page, "user": user(current),
        "plans": [plan(p) for p in ctx.get("plans", [])],
        "orders": [order(o, admin) for o in ctx.get("orders", [])],
        "recent": [order(o, admin) for o in ctx.get("recent", [])],
        "users": [user(u) for u in ctx.get("users", [])],
        "stats": ctx.get("stats", dict(users=0, verified=0, paid_users=0, orders_paid=0, revenue=0, unsynced=0)),
        "q": ctx.get("q", ""), "form": ctx.get("form", {}),
        "error": ctx.get("error"), "unverified": ctx.get("unverified", False),
        "flashes": flashes, "usage": ctx.get("usage"),
        "settings": {"nc_public_url": nc_public_url},
        "title": ctx.get("title", ""), "text": ctx.get("text", ""),
        "kind": ctx.get("kind", "info"), "link": ctx.get("link"),
    }
