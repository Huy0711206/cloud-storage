from datetime import timedelta
import re
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.models import User, utcnow
from app.core.security import hash_password, verify_password
from app.features.billing import service as billing
from app.shared import mailer
from app.shared.http import current_user, render
from .auth_models import PendingRegistration, PasswordReset
from .validation import _password_error
from . import otp

router = APIRouter()
GMAIL_RE = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@gmail\.com$", re.IGNORECASE)


def _pending(request, db):
    pending_id = request.session.get("pending_registration")
    pending = db.get(PendingRegistration, pending_id) if isinstance(pending_id, str) else None
    if not pending or pending.consumed_at or pending.expires_at <= utcnow():
        request.session.pop("pending_registration", None)
        return None
    return pending


def _verify_page(request, pending, *, error=None, sent=False, status_code=200):
    return render(request, "verify.html", form={"email": pending.email},
                  error=error, sent=sent, cooldown_seconds=otp.cooldown(pending), status_code=status_code)


def _verification_response(request, pending, sent, error, status):
    if sent:
        request.session["verification_sent"] = True
        return RedirectResponse("/verify", status_code=303)
    request.session.pop("verification_sent", None)
    return _verify_page(request, pending, error=error, sent=False, status_code=status)


def _bind_pending(request, db, *, email, full_name, password_hash, existing_user_id=None):
    request.session.pop("verification_sent", None)
    secret = otp.new_secret()
    pending = PendingRegistration(id=otp.digest("pending:"+secret), email=email,
                                  full_name=full_name, password_hash=password_hash,
                                  existing_user_id=existing_user_id,
                                  expires_at=utcnow()+timedelta(hours=24))
    db.add(pending)
    db.flush()
    request.session["pending_registration"] = pending.id
    return pending


@router.get("/register")
def register_form(request: Request, user: User | None = Depends(current_user)):
    if user:
        return RedirectResponse("/dashboard", status_code=303)
    # Returning to registration changes only this browser's binding, not an account.
    request.session.pop("pending_registration", None)
    request.session.pop("verification_sent", None)
    return render(request, "register.html", form={})


@router.post("/register")
def register(request: Request, full_name: str = Form(...), email: str = Form(...),
             password: str = Form(...), password2: str = Form(...), db: Session = Depends(get_db)):
    otp.same_origin(request)
    full_name, email = full_name.strip(), email.strip().lower()
    form = {"full_name": full_name, "email": email}
    def fail(message):
        return render(request, "register.html", status_code=400, form=form, error=message)
    if not full_name or len(full_name) > 120:
        return fail("Vui lòng nhập họ tên từ 1 đến 120 ký tự.")
    if len(email) > 200 or not GMAIL_RE.fullmatch(email):
        return fail("Vui lòng sử dụng địa chỉ Gmail thật có đuôi @gmail.com.")
    if password != password2:
        return fail("Hai mật khẩu không khớp.")
    if len(password) > 1024:
        return fail("Mật khẩu quá dài.")
    if error := _password_error(password):
        return fail(error.replace(" (yêu cầu của Nextcloud)", ""))
    otp.lock(db, "auth-identity")
    if not otp.consume_rate(db, "register-ip:"+otp.source_key(request), 30):
        db.commit()
        return render(request, "register.html", status_code=429, form=form,
                      error="Đã đạt giới hạn đăng ký từ kết nối này. Hãy thử lại sau.")
    if db.query(User).filter_by(email=email).first():
        return fail("Email này đã được đăng ký. Hãy đăng nhập hoặc khôi phục mật khẩu.")
    pending = _bind_pending(request, db, email=email, full_name=full_name,
                            password_hash=hash_password(password))
    sent, error, status = otp.send_code(db, pending, otp.source_key(request))
    db.commit()
    return _verification_response(request, pending, sent, error, status)


@router.get("/verify")
def verify_form(request: Request, db: Session = Depends(get_db)):
    pending = _pending(request, db)
    if not pending:
        return render(request, "message.html", title="Tiếp tục xác minh tài khoản",
                      text="Hãy đăng nhập nếu đã đăng ký, hoặc quay lại tạo tài khoản để nhận mã xác minh.",
                      kind="info", link=("/login", "Đăng nhập"))
    return _verify_page(request, pending, sent=bool(request.session.pop("verification_sent", False)))


@router.post("/verify")
def verify(request: Request, code: str = Form(""), db: Session = Depends(get_db)):
    otp.same_origin(request)
    otp.lock(db, "auth-identity")
    pending = _pending(request, db)
    if not pending:
        return RedirectResponse("/register", status_code=303)
    # Also bound failed verification requests per source, not only per browser.
    if not otp.consume_rate(db, "verify-ip:"+otp.source_key(request), 100):
        db.commit()
        return _verify_page(request, pending, error="Đã đạt giới hạn nhập mã. Hãy thử lại sau.", status_code=429)
    matched, error = otp.code_matches(pending, code.strip())
    if not matched:
        db.commit()
        return _verify_page(request, pending, error=error, status_code=400)
    user = db.query(User).filter_by(email=pending.email).with_for_update().first()
    if pending.existing_user_id:
        if not user or user.id != pending.existing_user_id or not user.is_active:
            db.rollback()
            return _verify_page(request, pending, error="Tài khoản không còn khả dụng.", status_code=400)
    elif user:
        # Concurrent registrations must not replace the first verified identity.
        db.rollback()
        return _verify_page(request, pending, error="Email đã có tài khoản. Hãy đăng nhập.", status_code=409)
    else:
        free = billing.free_plan(db)
        user = User(email=pending.email, full_name=pending.full_name, password_hash=pending.password_hash,
                    role="user", plan_id=free.id, nc_username=None, quota_synced=True)
        db.add(user)
        db.flush()
    user.is_verified = True
    pending.consumed_at, pending.code_hash = utcnow(), None
    pending.password_hash = ""
    # Any other browser's outstanding registration may no longer activate this email.
    db.query(PendingRegistration).filter(PendingRegistration.email == user.email,
                                        PendingRegistration.id != pending.id,
                                        PendingRegistration.consumed_at.is_(None)).update(
        {"consumed_at": utcnow(), "code_hash": None, "password_hash": ""})
    db.commit()
    request.session.clear()
    request.session["uid"] = user.id
    return RedirectResponse("/admin" if user.role == "admin" else "/dashboard", status_code=303)


@router.post("/resend")
def resend(request: Request, db: Session = Depends(get_db)):
    otp.same_origin(request)
    otp.lock(db, "auth-identity")
    pending = _pending(request, db)
    if not pending:
        return RedirectResponse("/register", status_code=303)
    sent, error, status = otp.send_code(db, pending, otp.source_key(request))
    db.commit()
    return _verification_response(request, pending, sent, error, status)


@router.get("/login")
def login_form(request: Request, user: User | None = Depends(current_user)):
    if user:
        return RedirectResponse("/admin" if user.role == "admin" else "/dashboard", status_code=303)
    return render(request, "login.html", form={})


@router.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    otp.same_origin(request)
    email = email.strip().lower()
    user = db.query(User).filter_by(email=email).first()
    def fail(message):
        return render(request, "login.html", status_code=400, form={"email": email}, error=message)
    if len(password) > 1024 or not user or not verify_password(password, user.password_hash):
        return fail("Email hoặc mật khẩu không đúng.")
    if not user.is_active:
        return fail("Tài khoản đã bị khóa. Hãy liên hệ quản trị viên.")
    if not user.is_verified:
        # End read transaction before taking the cross-process verification lock.
        uid = user.id
        db.rollback()
        otp.lock(db, "auth-identity")
        user = db.get(User, uid)
        pending = _bind_pending(request, db, email=user.email, full_name=user.full_name,
                                password_hash="", existing_user_id=user.id)
        sent, error, status = otp.send_code(db, pending, otp.source_key(request))
        db.commit()
        return _verification_response(request, pending, sent, error, status)
    request.session.clear()
    request.session["uid"] = user.id
    return RedirectResponse("/admin" if user.role == "admin" else "/dashboard", status_code=303)


@router.post("/logout")
def logout(request: Request):
    otp.same_origin(request)
    request.session.clear()
    return RedirectResponse("/", status_code=303)


@router.get("/forgot-password")
def forgot_form(request: Request):
    return render(request, "forgot.html", form={})


@router.post("/forgot-password")
def forgot(request: Request, email: str = Form(""), db: Session = Depends(get_db)):
    otp.same_origin(request)
    otp.lock(db, "auth-identity")
    email = email.strip().lower()[:255]
    allowed = otp.consume_rate(db, "reset-ip:"+otp.source_key(request), 20, minimum_wait=1)
    allowed = allowed and otp.consume_rate(db, "reset-email:"+email, 5, minimum_wait=60)
    user = db.query(User).filter_by(email=email, is_active=True, is_verified=True).first() if allowed else None
    if user:
        secret = otp.new_secret()
        # Invalidate any earlier reset in the same account, including concurrently requested links.
        db.query(PasswordReset).filter_by(user_id=user.id, consumed_at=None).update({"consumed_at": utcnow()})
        reset = PasswordReset(id=otp.digest("reset:"+secret), user_id=user.id,
                              expires_at=utcnow()+timedelta(minutes=30))
        db.add(reset)
        try:
            mailer.send_password_reset(user.email, user.full_name,
                                       settings.base_url+"/reset-password?token="+secret)
        except mailer.MailDeliveryError:
            reset.consumed_at = utcnow()
    db.commit()
    return render(request, "message.html", title="Yêu cầu khôi phục tài khoản",
                  text="Nếu tài khoản phù hợp tồn tại và dịch vụ email sẵn sàng, bạn sẽ nhận được liên kết đặt lại mật khẩu. Hãy kiểm tra cả thư mục spam.",
                  kind="info", link=("/login", "Về đăng nhập"))


@router.get("/reset-password")
def reset_form(request: Request, token: str = "", db: Session = Depends(get_db)):
    reset = db.get(PasswordReset, otp.digest("reset:"+token)) if token else None
    if not reset or reset.consumed_at or reset.expires_at <= utcnow():
        return render(request, "message.html", status_code=400, title="Liên kết không hợp lệ",
                      text="Liên kết đã dùng hoặc hết hạn. Hãy yêu cầu khôi phục lại.", kind="error",
                      link=("/forgot-password", "Khôi phục tài khoản"))
    response = render(request, "reset.html", reset_token=token, form={})
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


@router.post("/reset-password")
def reset_password(request: Request, token: str = Form(""), password: str = Form(""),
                   password2: str = Form(""), db: Session = Depends(get_db)):
    otp.same_origin(request)
    otp.lock(db, "auth-identity")
    reset = db.get(PasswordReset, otp.digest("reset:"+token)) if token else None
    if not reset or reset.consumed_at or reset.expires_at <= utcnow():
        return render(request, "reset.html", status_code=400, reset_token="",
                      error="Liên kết đã dùng hoặc hết hạn. Hãy yêu cầu khôi phục lại.")
    error = "Hai mật khẩu không khớp." if password != password2 else _password_error(password)
    if len(password) > 1024:
        error = "Mật khẩu quá dài."
    if error:
        return render(request, "reset.html", status_code=400, reset_token=token,
                      error=error.replace(" (yêu cầu của Nextcloud)", ""))
    user = db.get(User, reset.user_id)
    if not user or not user.is_active or not user.is_verified:
        return render(request, "reset.html", status_code=400, reset_token="", error="Tài khoản không còn khả dụng.")
    user.password_hash = hash_password(password)
    reset.consumed_at = utcnow()
    db.commit()
    request.session.clear()
    return render(request, "message.html", title="Đã đặt lại mật khẩu",
                  text="Hãy đăng nhập bằng mật khẩu CloudBox mới.", kind="ok", link=("/login", "Đăng nhập"))
