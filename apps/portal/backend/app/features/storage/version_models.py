"""Additive metadata for native revisions; existing imported history is untouched."""
from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ReplacementUpload(Base):
    __tablename__ = "storage_replacement_uploads"
    upload_id: Mapped[str] = mapped_column(ForeignKey("storage_uploads.id", ondelete="CASCADE"), primary_key=True)
    # No node FK: purging a file must not be blocked by completed upload receipts.
    node_id: Mapped[str] = mapped_column(String(32), index=True)
    expected_blob_key: Mapped[str] = mapped_column(String(32))


class VersionPolicy(Base):
    __tablename__ = "storage_version_policies"
    version_id: Mapped[str] = mapped_column(ForeignKey("storage_versions.id", ondelete="CASCADE"), primary_key=True)
    expires_at: Mapped[object] = mapped_column(DateTime, index=True)
    plan_code: Mapped[str] = mapped_column(String(30))
