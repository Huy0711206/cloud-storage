from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from .. import nextcloud, services
from ..db import get_db
from ..deps import render, require_user
from ..models import Order, Plan, User
from ..nextcloud import NextcloudError

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
