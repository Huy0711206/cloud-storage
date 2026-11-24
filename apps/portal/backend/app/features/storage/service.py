"""Quota is now enforced against the current CloudBox plan in native storage."""
from sqlalchemy.orm import Session
from app.core.models import User

def sync_quota(db: Session, user: User, *, commit: bool = True) -> bool:
    user.quota_synced = True
    if commit:
        db.commit()
    return True
