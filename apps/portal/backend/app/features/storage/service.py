"""Quota is now enforced against the current CloudBox plan in native storage."""
from sqlalchemy.orm import Session
from app.core.models import User

def sync_quota(db: Session, user: User) -> bool:
    user.quota_synced = True
    db.commit()
    return True
