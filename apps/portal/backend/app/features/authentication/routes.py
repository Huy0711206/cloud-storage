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
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$" )

router = APIRouter()

def _send_verification(background: BackgroundTasks, user: User) -> None:
    link = f"{settings.base_url}/verify?token={make_verify_token(user.email)}"
    background.add_task(emailer.send_verification, user.email, user.full_name, link)



@router.get("/register")
def register_form(request: Request, user: User | None = Depends(current_user)):
    if user:
        return RedirectResponse("/dashboard", status_code=303)
    return render(request, "register.html", None, form={})



@router.post("/register")
def register(request: Request, background: BackgroundTasks,
             full_name: str = Form(...), email: str = Form(...),
             password: str = Form(...), password2: str = Form(...),
             db: Session = Depends(get_db)):
    full_name, email = full_name.strip(), email.strip().lower()
    form = {"full_name": full_name, "email": email}

    def fail(msg: str):
        return render(request, "register.html", None, status_code=400, form=form, error=msg)

    if not full_name:
        return fail("Vui lòng nhập họ tên.")
    if not EMAIL_RE.match(email) or len(email) > 200:
        return fail("Email không hợp lệ.")
    if password != password2:
        return fail("Hai mật khẩu không khớp.")
    if (err := _password_error(password)):
        return fail(err)

    existing = db.query(User).filter_by(email=email).first()
    if existing:
        if not existing.is_verified:
            return fail("Email này đã đăng ký nhưng chưa xác thực. Hãy kiểm tra hộp thư hoặc bấm "
                        "'Gửi lại email xác thực' ở trang đăng nhập.")
        return fail("Email này đã được đăng ký.")

    free = services.free_plan(db)
    user = User(email=email, full_name=full_name, password_hash=hash_password(password),
                role="user", nc_username=email, plan_id=free.id)
    db.add(user)
    db.flush()
    try:
        storage_services.provision_nextcloud_account(email, password, full_name, free.quota_gb)
    except NextcloudError as exc:
        db.rollback()
        if exc.code == 102:
            return fail("Tên tài khoản đã tồn tại trên Nextcloud. Hãy liên hệ quản trị viên.")
        return fail(f"Không tạo được kho lưu trữ: {exc}")
    db.commit()

    _send_verification(background, user)
    return render(request, "message.html", None, title="Kiểm tra email của bạn",
                  text=f"Chúng tôi đã gửi liên kết xác thực tới {email}. Bấm vào liên kết đó để kích hoạt tài khoản.",
                  kind="ok")



@router.get("/verify")
def verify(request: Request, token: str = "", db: Session = Depends(get_db)):
    email = read_verify_token(token)
    user = db.query(User).filter_by(email=email).first() if email else None
    if not user:
        return render(request, "message.html", None, status_code=400, title="Liên kết không hợp lệ",
                      text="Liên kết xác thực không đúng hoặc đã hết hạn. Hãy yêu cầu gửi lại email xác thực.",
                      kind="error")
    if not user.is_verified:
        try:
            if user.is_active:
                nextcloud.nc.enable_user(user.nc_username)
        except NextcloudError as exc:
            return render(request, "message.html", None, status_code=502, title="Chưa kích hoạt được",
                          text=f"Không mở được kho lưu trữ: {exc}. Hãy thử lại sau ít phút.", kind="error")
        user.is_verified = True
        db.commit()
    return render(request, "message.html", None, title="Xác thực thành công",
                  text="Tài khoản đã được kích hoạt. Bạn có thể đăng nhập.", kind="ok",
                  link=("/login", "Đăng nhập"))



@router.post("/resend")
def resend(request: Request, background: BackgroundTasks, email: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=email.strip().lower()).first()
    if user and not user.is_verified:
        _send_verification(background, user)
    # luôn trả lời giống nhau để không lộ email nào đã đăng ký
    return render(request, "message.html", None, title="Đã gửi lại email",
                  text="Nếu email này đã đăng ký và chưa xác thực, bạn sẽ nhận được liên kết mới trong ít phút.",
                  kind="ok")



@router.get("/login")
def login_form(request: Request, user: User | None = Depends(current_user)):
    if user:
        return RedirectResponse("/dashboard", status_code=303)
    return render(request, "login.html", None, form={})



@router.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    email = email.strip().lower()
    user = db.query(User).filter_by(email=email).first()

    def fail(msg: str, unverified: bool = False):
        return render(request, "login.html", None, status_code=400, form={"email": email},
                      error=msg, unverified=unverified)

    if not user or not verify_password(password, user.password_hash):
        return fail("Email hoặc mật khẩu không đúng.")
    if not user.is_active:
        return fail("Tài khoản đã bị khóa. Hãy liên hệ quản trị viên.")
    if not user.is_verified:
        return fail("Tài khoản chưa xác thực email.", unverified=True)
    request.session.clear()
    request.session["uid"] = user.id
    return RedirectResponse("/admin" if user.role == "admin" else "/dashboard", status_code=303)



@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)

