import re

from fastapi import APIRouter, BackgroundTasks, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from .. import emailer, nextcloud, services
from ..config import settings
from ..db import get_db
from ..deps import current_user, flash, render, require_user
from ..models import Plan, User
from ..nextcloud import NextcloudError
from ..security import hash_password, make_verify_token, read_verify_token, verify_password

router = APIRouter()
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _password_error(password: str) -> str | None:
    if len(password) < 10:
        return "Mật khẩu phải có ít nhất 10 ký tự (yêu cầu của Nextcloud)."
    if not (re.search(r"[A-Za-z]", password) and re.search(r"\d", password)):
        return "Mật khẩu phải gồm cả chữ và số."
    return None


def _send_verification(background: BackgroundTasks, user: User) -> None:
    link = f"{settings.base_url}/verify?token={make_verify_token(user.email)}"
    background.add_task(emailer.send_verification, user.email, user.full_name, link)


@router.get("/")
def home(request: Request, db: Session = Depends(get_db), user: User | None = Depends(current_user)):
    plans = db.query(Plan).filter(Plan.is_active.is_(True)).order_by(Plan.sort).all()
    return render(request, "home.html", user, plans=plans)


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
        services.provision_nextcloud_account(email, password, full_name, free.quota_gb)
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
