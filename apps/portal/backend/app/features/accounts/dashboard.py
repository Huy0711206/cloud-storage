import re
import secrets
from fastapi import APIRouter, BackgroundTasks, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.core.models import Order, Plan, User
from app.core.security import hash_password, make_verify_token, read_verify_token, verify_password
from app.shared import mailer as emailer
from app.shared.http import current_user, dt, flash, render, require_user, require_admin
from app.features.storage import client as nextcloud
from app.features.storage.client import NextcloudError
from app.features.billing import service as services
from app.features.storage import service as storage_services
from app.features.payments import service as payment_services
from app.features.payments import vnpay

router = APIRouter()

@router.get("/dashboard")
def dashboard(request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
    if user.role == "admin":
        return RedirectResponse("/admin", status_code=303)

    usage = None
    if user.nc_username:
        try:
            used, total = nextcloud.nc.get_usage(user.nc_username)
            total = total or user.plan.quota_gb * 1024**3
            usage = {"used": used, "total": total, "percent": min(100, round(used * 100 / total)) if total else 0}
        except NextcloudError:
            usage = None  # Nextcloud tạm thời không trả lời: vẫn hiển thị trang

    plans = db.query(Plan).filter(Plan.is_active.is_(True)).order_by(Plan.sort).all()
    orders = (db.query(Order).filter_by(user_id=user.id).order_by(Order.id.desc()).limit(20).all())
    return render(request, "dashboard.html", user, usage=usage, plans=plans, orders=orders,
                  month_choices=services.MONTH_CHOICES, calc_amount=services.calc_amount)

