"""Additive metadata for favorites, in-app notifications and team activity."""
from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.models import utcnow


class FileFavorite(Base):
    __tablename__ = "storage_favorites"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    node_id: Mapped[str] = mapped_column(ForeignKey("storage_nodes.id", ondelete="CASCADE"), primary_key=True, index=True)


class WorkspaceNotice(Base):
    __tablename__ = "workspace_notices"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    kind: Mapped[str] = mapped_column(String(20))
    label: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[object] = mapped_column(DateTime, default=utcnow)
    read_at: Mapped[object | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (Index("ix_workspace_notices_feed", "user_id", "kind", "created_at"),)


class TeamActivity(Base):
    __tablename__ = "storage_team_activity"

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[str] = mapped_column(ForeignKey("storage_teams.id", ondelete="CASCADE"))
    actor: Mapped[str] = mapped_column(String(120))
    action: Mapped[str] = mapped_column(String(18))
    name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[object] = mapped_column(DateTime, default=utcnow)

    __table_args__ = (Index("ix_storage_team_activity_feed", "team_id", "id"),)
