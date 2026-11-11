from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.models import Order, Plan, User
from app.shared.http import render, require_user
from app.features.billing import service as services

router = APIRouter()

@router.get("/dashboard")
def dashboard(request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
    if user.role == "admin":
        return RedirectResponse("/admin", status_code=303)

    from app.features.storage.native_service import quota_usage
    usage = quota_usage(db, user)

    plans = db.query(Plan).filter(Plan.is_active.is_(True)).order_by(Plan.sort).all()
    orders = (db.query(Order).filter_by(user_id=user.id).order_by(Order.id.desc()).limit(20).all())
    return render(request, "dashboard.html", user, usage=usage, plans=plans, orders=orders,
                  month_choices=services.MONTH_CHOICES, calc_amount=services.calc_amount)


@router.get("/files")
def files_workspace(request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
    from app.features.storage.native_service import quota_usage
    return render(request, "dashboard.html", user, usage=quota_usage(db,user),
                  plans=db.query(Plan).filter(Plan.is_active.is_(True)).order_by(Plan.sort).all(),
                  orders=db.query(Order).filter_by(user_id=user.id).order_by(Order.id.desc()).limit(20).all())
