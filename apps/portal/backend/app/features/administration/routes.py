from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import Session, contains_eager
from app.core.database import get_db
from app.core.models import Order, Plan, User, utcnow
from app.shared.http import flash, render, require_admin
from app.features.billing import service as services
from app.features.billing.entitlements import effective_plan
from app.features.storage import service as storage_services
from .audit import AdminAuditEntry, audit_view, plan_state
from .health import diagnostics

router = APIRouter(prefix='/admin')

def _back(url: str = "/admin/users"):
    return RedirectResponse(url, status_code=303)


@router.get("")
def overview(request: Request, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    now = utcnow()
    paid_candidates = (db.query(User).join(User.plan).options(contains_eager(User.plan))
                       .filter(User.role == "user", Plan.price_vnd > 0).yield_per(256))
    stats = {
        "users": db.query(User).filter(User.role == "user").count(),
        "verified": db.query(User).filter(User.role == "user", User.is_verified.is_(True)).count(),
        "paid_users": sum(effective_plan(user, at=now) is not None for user in paid_candidates),
        "orders_paid": db.query(Order).filter_by(status="paid").count(),
        "revenue": db.query(func.coalesce(func.sum(Order.amount_vnd), 0)).filter_by(status="paid").scalar(),
        "unsynced": db.query(User).filter(User.quota_synced.is_(False)).count(),
    }
    recent = db.query(Order).order_by(Order.id.desc()).limit(8).all()
    return render(request, "admin_overview.html", admin, stats=stats, recent=recent)


@router.get("/diagnostics")
def system_diagnostics(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return diagnostics(db)


@router.get("/audit")
def audit_log(request: Request, page: int = Query(1, ge=1), db: Session = Depends(get_db),
              admin: User = Depends(require_admin)):
    page_size = 25
    query = db.query(AdminAuditEntry)
    pages = max(1, (query.count() + page_size - 1) // page_size)
    page = min(page, pages)
    entries = (query.order_by(AdminAuditEntry.created_at.desc(), AdminAuditEntry.id.desc())
               .offset((page - 1) * page_size).limit(page_size).all())
    return render(request, "admin_audit.html", admin, audit={
        "entries": [audit_view(entry) for entry in entries], "page": page, "pages": pages,
    })


def _locked_user(db: Session, user_id: int) -> User | None:
    return db.query(User).filter_by(id=user_id, role="user").populate_existing().with_for_update().one_or_none()


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
    user = _locked_user(db, user_id)
    if not user:
        flash(request, "Không tìm thấy người dùng.", "error")
        return _back()
    new_state = not user.is_active
    user.is_active = new_state
    db.add(AdminAuditEntry(actor_id=admin.id, action="account_lock", subject_id=user.id,
                           before={"is_active": not new_state}, after={"is_active": new_state}))
    db.commit()
    flash(request, f"Đã {'mở khóa' if new_state else 'khóa'} {user.email}.", "ok")
    return _back()


@router.post("/users/{user_id}/grant")
def grant_plan(request: Request, user_id: int, plan_code: str = Form(...), months: int = Form(1),
               db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    user = _locked_user(db, user_id)
    plan = db.query(Plan).filter_by(code=plan_code).first()
    if not user or not plan:
        flash(request, "Dữ liệu không hợp lệ.", "error")
        return _back()
    if plan.price_vnd > 0 and months not in services.MONTH_CHOICES:
        flash(request, "Thời hạn không hợp lệ.", "error")
        return _back()
    before = plan_state(db, user)
    if plan.price_vnd == 0:
        services.set_free(db, user, commit=False)
        message = f"Đã chuyển {user.email} về gói {plan.name}."
    else:
        services.activate_plan(db, user, plan, months, commit=False)
        message = f"Đã cấp gói {plan.name} ({months} tháng) cho {user.email}."
    db.add(AdminAuditEntry(actor_id=admin.id, action="plan_grant", subject_id=user.id,
                           before=before, after=plan_state(db, user)))
    db.commit()
    flash(request, message, "ok")
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
    plan = db.query(Plan).filter_by(id=plan_id).with_for_update(key_share=True).one_or_none()
    if not plan or quota_gb < 1 or price_vnd < 0 or (plan.price_vnd == 0 and price_vnd != 0):
        flash(request, "Dữ liệu gói không hợp lệ (gói Miễn phí phải giữ giá 0).", "error")
        return _back("/admin/plans")
    quota_changed = plan.quota_gb != quota_gb
    if plan.price_vnd != price_vnd:
        db.add(AdminAuditEntry(actor_id=admin.id, action="plan_price", subject_id=plan.id,
                               before={"price_vnd": plan.price_vnd}, after={"price_vnd": price_vnd}))
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

