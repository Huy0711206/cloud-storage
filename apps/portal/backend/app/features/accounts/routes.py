from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.models import User
from app.core.security import hash_password, verify_password
from app.shared.http import flash, require_user
from app.features.authentication.validation import _password_error

router = APIRouter()

@router.post("/account/password")
def change_password(request: Request, current: str = Form(...), new: str = Form(...), new2: str = Form(...),
                    db: Session = Depends(get_db), user: User = Depends(require_user)):
    if not verify_password(current, user.password_hash):
        flash(request, "Mật khẩu hiện tại không đúng.", "error")
    elif new != new2:
        flash(request, "Hai mật khẩu mới không khớp.", "error")
    elif len(new) > 1024:
        flash(request, "Mật khẩu quá dài.", "error")
    elif (err := _password_error(new)):
        flash(request, err, "error")
    else:
        user.password_hash = hash_password(new)
        db.commit()
        flash(request, "Đã đổi mật khẩu CloudBox.", "ok")
    return RedirectResponse("/dashboard#settings", status_code=303)

