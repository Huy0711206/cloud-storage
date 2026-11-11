"""Retained source history and migration proof; never contains account secrets."""
from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.core.models import utcnow
from .native_models import identifier

class FileVersion(Base):
    __tablename__ = 'storage_versions'
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=identifier)
    owner_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    node_id: Mapped[str | None] = mapped_column(ForeignKey('storage_nodes.id'), nullable=True, index=True)
    source_key: Mapped[str] = mapped_column(String(1024), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    size: Mapped[int] = mapped_column(BigInteger, default=0)
    blob_key: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[object] = mapped_column(DateTime, default=utcnow)

class MigrationRecord(Base):
    __tablename__ = 'storage_migration_records'
    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    payload: Mapped[str] = mapped_column(Text)
    created_at: Mapped[object] = mapped_column(DateTime, default=utcnow)
