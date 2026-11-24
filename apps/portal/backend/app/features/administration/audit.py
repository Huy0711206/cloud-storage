"""Transactions attach an audit entry before committing their changes."""
from datetime import datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.models import Plan, User, utcnow
from app.shared.http import dt, vnd


class AdminAuditEntry(Base):
    __tablename__ = "admin_audit_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    actor_id: Mapped[int]
    action: Mapped[str] = mapped_column(String(20))
    subject_id: Mapped[int]
    before: Mapped[dict] = mapped_column(JSON)
    after: Mapped[dict] = mapped_column(JSON)


def plan_state(db, user: User) -> dict:
    plan = db.get(Plan, user.plan_id) if user.plan_id is not None else None
    return {
        "plan_code": plan.code if plan else None,
        "expires_at": user.plan_expires_at.isoformat() if user.plan_expires_at else None,
    }


def _summary(action: str, values: dict) -> str:
    if action == "account_lock":
        return "Đang hoạt động" if values["is_active"] else "Đã khóa"
    if action == "plan_grant":
        expires = values["expires_at"]
        code = values["plan_code"]
        return f"{code} · Hạn đến {dt(datetime.fromisoformat(expires))}" if expires else (code or "Chưa có gói")
    return vnd(values["price_vnd"])


def audit_view(entry: AdminAuditEntry) -> dict:
    if entry.action == "account_lock":
        label = "Mở khóa tài khoản" if entry.after["is_active"] else "Khóa tài khoản"
    else:
        label = {"plan_grant": "Cấp gói", "plan_price": "Đổi giá gói"}[entry.action]
    subject = "Gói" if entry.action == "plan_price" else "Tài khoản"
    return {
        "id": entry.id,
        "created_at": entry.created_at.isoformat() + "Z",
        "actor_id": entry.actor_id,
        "action": label,
        "subject": f"{subject} #{entry.subject_id}",
        "before": _summary(entry.action, entry.before),
        "after": _summary(entry.action, entry.after),
    }
