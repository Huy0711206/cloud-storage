from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    """Thời điểm hiện tại theo UTC (không kèm tzinfo để tương thích SQLite/Postgres)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(60))
    quota_gb: Mapped[int] = mapped_column(Integer)
    price_vnd: Mapped[int] = mapped_column(Integer, default=0)  # giá cho 1 tháng
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort: Mapped[int] = mapped_column(Integer, default=0)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(10), default="user")  # "user" | "admin"
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    nc_username: Mapped[str | None] = mapped_column(String(255), nullable=True)  # None với admin portal
    plan_id: Mapped[int | None] = mapped_column(ForeignKey("plans.id"), nullable=True)
    plan_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    quota_synced: Mapped[bool] = mapped_column(Boolean, default=True)  # quota trên Nextcloud đã khớp gói chưa
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    plan: Mapped[Plan | None] = relationship()


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"))
    months: Mapped[int] = mapped_column(Integer)
    amount_vnd: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(10), default="pending")  # pending | paid | failed
    txn_ref: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    gateway_txn_no: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped[User] = relationship()
    plan: Mapped[Plan] = relationship()
