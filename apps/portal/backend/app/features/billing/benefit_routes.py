from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.features.storage.capacity import pool_limit, pool_usage
from app.core.models import User
from app.shared.http import current_user
from .entitlements import BENEFITS, benefits_for_code, benefits_for_user

router = APIRouter()

@router.get("/api/plan-benefits")
def plan_benefits(user: User | None = Depends(current_user), db: Session = Depends(get_db)):
    return {"deployment": {"trial": bool(pool_limit()), "storage_pool_limit_bytes": pool_limit()}, "capacity": pool_usage(db) if user and user.role == "admin" else None, "plans": {code: benefits_for_code(code) for code in BENEFITS}, "current": benefits_for_user(user) if user else benefits_for_code("free")}
