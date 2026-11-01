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

router = APIRouter(prefix='/admin')

def _back(url: str = "/admin/users"):
    return RedirectResponse(url, status_code=303)



@router.get("")
def overview(request: Request, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    stats = {
        "users": db.query(User).filter(User.role == "user").count(),
        "verified": db.query(User).filter(User.role == "user", User.is_verified.is_(True)).count(),
        "paid_users": db.query(User).filter(User.plan_expires_at.is_not(None)).count(),
        "orders_paid": db.query(Order).filter_by(status="paid").count(),
        "revenue": db.query(func.coalesce(func.sum(Order.amount_vnd), 0)).filter_by(status="paid").scalar(),
        "unsynced": db.query(User).filter(User.quota_synced.is_(False)).count(),
    }
    recent = db.query(Order).order_by(Order.id.desc()).limit(8).all()
    return render(request, "admin_overview.html", admin, stats=stats, recent=recent)



@router.get("/users")
def users(request: Request, q: str = "", db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    query = db.query(User).filter(User.role == "user")
    if q.strip():
        like = f"%{q.strip().lower()}%"
        query = query.filter(User.email.like(like) | func.lower(User.full_name).like(like))
    plans = db.query(Plan).order_by(Plan.sort).all()
    return render(request, "admin_users.html", admin, users=query.order_by(User.id.desc()).limit(200).all(),
                  plans=plans, q=q, month_choices=services.MONTH_CHOICES)



@router.post("/users/{user_id}/toggle")
def toggle_user(request: Request, user_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    user = db.get(User, user_id)
    if not user or user.role != "user":
        flash(request, "Không tìm thấy người dùng.", "error")
        return _back()
    new_state = not user.is_active
    try:
        if user.nc_username and user.is_verified:
            (nextcloud.nc.enable_user if new_state else nextcloud.nc.disable_user)(user.nc_username)
    except NextcloudError as exc:
        flash(request, f"Không đổi được trạng thái trên Nextcloud: {exc}", "error")
        return _back()
    user.is_active = new_state
    db.commit()
    flash(request, f"Đã {'mở khóa' if new_state else 'khóa'} {user.email}.", "ok")
    return _back()



@router.post("/users/{user_id}/grant")
def grant_plan(request: Request, user_id: int, plan_code: str = Form(...), months: int = Form(1),
               db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    user = db.get(User, user_id)
    plan = db.query(Plan).filter_by(code=plan_code).first()
    if not user or user.role != "user" or not plan:
        flash(request, "Dữ liệu không hợp lệ.", "error")
    elif plan.price_vnd == 0:
        services.set_free(db, user)
        flash(request, f"Đã chuyển {user.email} về gói {plan.name}.", "ok")
    elif months not in services.MONTH_CHOICES:
        flash(request, "Thời hạn không hợp lệ.", "error")
    else:
        services.activate_plan(db, user, plan, months)
        flash(request, f"Đã cấp gói {plan.name} ({months} tháng) cho {user.email}.", "ok")
    return _back()



@router.post("/users/{user_id}/sync")
def sync_user(request: Request, user_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    user = db.get(User, user_id)
    if user and storage_services.sync_quota(db, user):
        flash(request, f"Đã đồng bộ quota cho {user.email}.", "ok")
    else:
        flash(request, "Đồng bộ thất bại, xem log của portal.", "error")
    return _back()



@router.get("/orders")
def orders(request: Request, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    rows = db.query(Order).order_by(Order.id.desc()).limit(200).all()
    return render(request, "admin_orders.html", admin, orders=rows)



@router.get("/plans")
def plans(request: Request, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return render(request, "admin_plans.html", admin, plans=db.query(Plan).order_by(Plan.sort).all())



@router.post("/plans/{plan_id}")
def update_plan(request: Request, plan_id: int, name: str = Form(...), quota_gb: int = Form(...),
                price_vnd: int = Form(...), is_active: str = Form(""),
                db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    plan = db.get(Plan, plan_id)
    if not plan or quota_gb < 1 or price_vnd < 0 or (plan.price_vnd == 0 and price_vnd != 0):
        flash(request, "Dữ liệu gói không hợp lệ (gói Miễn phí phải giữ giá 0).", "error")
        return _back("/admin/plans")
    quota_changed = plan.quota_gb != quota_gb
    plan.name, plan.quota_gb, plan.price_vnd = name.strip() or plan.name, quota_gb, price_vnd
    plan.is_active = bool(is_active) or plan.price_vnd == 0  # không cho tắt gói Miễn phí
    if quota_changed:
        for u in db.query(User).filter(User.plan_id == plan.id).all():
            u.quota_synced = False
    db.commit()
    if quota_changed:
        services.run_maintenance(db)
    flash(request, f"Đã cập nhật gói {plan.name}.", "ok")
    return _back("/admin/plans")



@router.post("/maintenance")
def maintenance(request: Request, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    n = services.run_maintenance(db)
    flash(request, f"Đã chạy bảo trì: hạ {n} tài khoản hết hạn, đồng bộ lại quota còn thiếu.", "ok")
    return _back("/admin")

