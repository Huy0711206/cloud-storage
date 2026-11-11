"""Additive share controls; existing bearer links keep their original semantics."""
from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.core.models import utcnow


class ShareProtection(Base):
    __tablename__ = "storage_share_protection"
    share_id: Mapped[str] = mapped_column(ForeignKey("storage_shares.id", ondelete="CASCADE"), primary_key=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)


class ShareStatistics(Base):
    __tablename__ = "storage_share_statistics"
    share_id: Mapped[str] = mapped_column(ForeignKey("storage_shares.id", ondelete="CASCADE"), primary_key=True)
    views: Mapped[int] = mapped_column(Integer, default=0)
    downloads: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[object] = mapped_column(DateTime, default=utcnow)
