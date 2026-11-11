"""Native CloudBox storage metadata; blob bytes are kept on persistent disk."""
import uuid

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.models import utcnow


def identifier() -> str:
    return uuid.uuid4().hex


class FileNode(Base):
    __tablename__ = "storage_nodes"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=identifier)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("storage_nodes.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    is_folder: Mapped[bool] = mapped_column(Boolean, default=False)
    size: Mapped[int] = mapped_column(BigInteger, default=0)
    blob_key: Mapped[str | None] = mapped_column(String(32), nullable=True, unique=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mime_type: Mapped[str] = mapped_column(String(150), default="application/octet-stream")
    modified_at: Mapped[object] = mapped_column(DateTime, default=utcnow)
    deleted_at: Mapped[object | None] = mapped_column(DateTime, nullable=True, index=True)
    trash_root_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    legacy_file_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    legacy_storage: Mapped[str | None] = mapped_column(String(255), nullable=True)
    __table_args__ = (Index("ix_storage_siblings", "owner_id", "parent_id", "name"),)


class UploadSession(Base):
    __tablename__ = "storage_uploads"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=identifier)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("storage_nodes.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255))
    size: Mapped[int] = mapped_column(BigInteger)
    received: Mapped[int] = mapped_column(BigInteger, default=0)
    created_at: Mapped[object] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[object] = mapped_column(DateTime, index=True)
    state: Mapped[str] = mapped_column(String(12), default="pending", index=True)
    node_id: Mapped[str | None] = mapped_column(String(32), nullable=True)


class FileShare(Base):
    __tablename__ = "storage_shares"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=identifier)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    node_id: Mapped[str] = mapped_column(ForeignKey("storage_nodes.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[object] = mapped_column(DateTime, default=utcnow)
    revoked_at: Mapped[object | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[object | None] = mapped_column(DateTime, nullable=True)
    legacy_share_id: Mapped[str | None] = mapped_column(String(64), nullable=True)


class StorageGarbage(Base):
    """Durable physical-deletion queue, populated in the metadata deletion transaction."""
    __tablename__ = "storage_garbage"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=identifier)
    kind: Mapped[str] = mapped_column(String(10))
    object_key: Mapped[str] = mapped_column(String(32), index=True)
    created_at: Mapped[object] = mapped_column(DateTime, default=utcnow)
