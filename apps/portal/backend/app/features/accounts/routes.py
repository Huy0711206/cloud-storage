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
from app.features.authentication.validation import _password_error

router = APIRouter()

@router.post("/account/password")
def change_password(request: Request, current: str = Form(...), new: str = Form(...), new2: str = Form(...),
                    db: Session = Depends(get_db), user: User = Depends(require_user)):
    if not verify_password(current, user.password_hash):
        flash(request, "Mật khẩu hiện tại không đúng.", "error")
    elif new != new2:
        flash(request, "Hai mật khẩu mới không khớp.", "error")
    elif (err := _password_error(new)):
        flash(request, err, "error")
    else:
        try:
            if user.nc_username:
                nextcloud.nc.set_password(user.nc_username, new)
        except NextcloudError as exc:
            flash(request, f"Không đổi được mật khẩu trên kho lưu trữ: {exc}", "error")
            return RedirectResponse("/dashboard#settings", status_code=303)
        user.password_hash = hash_password(new)
        db.commit()
        flash(request, "Đã đổi mật khẩu (áp dụng cho cả cổng này và kho lưu trữ).", "ok")
    return RedirectResponse("/dashboard#settings", status_code=303)

