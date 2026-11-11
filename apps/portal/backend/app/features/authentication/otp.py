"""Transactional OTP and recovery helpers. No plaintext codes are persisted."""
import hashlib
import hmac
import re
import secrets
from datetime import timedelta

from fastapi import HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.models import utcnow
from app.shared import mailer
from .auth_models import AuthRateLimit, PendingRegistration, PasswordReset

CODE_TTL = 600
MAX_ATTEMPTS = 5
RESEND_WAIT = 60


def digest(value: str) -> str:
    return hmac.new(settings.secret_key.encode(), value.encode(), hashlib.sha256).hexdigest()


def new_secret() -> str:
    return secrets.token_urlsafe(32)


def same_origin(request: Request) -> None:
    from app.shared.csrf import origin_allowed
    if not origin_allowed(request,settings.base_url):
        raise HTTPException(403,"Phiên biểu mẫu không hợp lệ. Hãy mở lại CloudBox.")


def lock(db: Session, *keys: str) -> None:
    """PG advisory locks also protect rate rows before they exist.

    Call before the first query. SQLite's immediate write transaction makes the
    same read/check/write boundary serial across processes, not only threads.
    """
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        for key in sorted(set(keys)):
            value = int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "big", signed=True)
            db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": value})
    elif dialect == "sqlite":
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")


def source_key(request: Request) -> str:
    # Use server-resolved client only; arbitrary X-Forwarded-For is not trusted here.
    return request.client.host if request.client else "unknown"


def consume_rate(db: Session, name: str, limit: int, *, minimum_wait: int = 0) -> bool:
    key = digest("rate:" + name)
    now = utcnow()
    row = db.get(AuthRateLimit, key)
    if row is None:
        row = AuthRateLimit(key=key, window_started=now, count=0, last_at=now-timedelta(hours=1))
        db.add(row)
    if row.window_started <= now - timedelta(hours=1):
        row.window_started, row.count = now, 0
    if row.count >= limit or row.last_at > now-timedelta(seconds=minimum_wait):
        return False
    row.count += 1
    row.last_at = now
    db.flush()
    return True


def cooldown(pending: PendingRegistration) -> int:
    if not pending.last_sent_at:
        return 0
    return max(0, RESEND_WAIT - int((utcnow()-pending.last_sent_at).total_seconds()))


def send_code(db: Session, pending: PendingRegistration, ip: str) -> tuple[bool, str | None, int]:
    # Both quotas are checked under the caller's advisory/SQLite write lock.
    if not consume_rate(db, "otp-email:"+pending.email, 5, minimum_wait=RESEND_WAIT):
        return False, "Bạn đã gửi quá nhanh hoặc đạt giới hạn 5 lần/giờ. Hãy thử lại sau.", 429
    if not consume_rate(db, "otp-ip:"+ip, 20, minimum_wait=1):
        return False, "Đã đạt giới hạn gửi mã từ kết nối này. Hãy thử lại sau.", 429
    code = f"{secrets.randbelow(1_000_000):06d}"
    if pending.code_hash and hmac.compare_digest(
        digest("otp:"+pending.id+":"+code), pending.code_hash
    ):
        code = f"{(int(code)+1) % 1_000_000:06d}"
    pending.code_hash = digest("otp:"+pending.id+":"+code)
    pending.attempts = 0
    pending.code_expires_at = utcnow()+timedelta(seconds=CODE_TTL)
    pending.last_sent_at = utcnow()
    try:
        mailer.send_verification_code(pending.email, pending.full_name, code)
    except mailer.MailDeliveryError:
        pending.code_hash = None
        pending.code_expires_at = None
        return False, "Chưa gửi được mã xác minh. Hãy chờ rồi gửi lại hoặc liên hệ quản trị viên.", 503
    return True, None, 200


def code_matches(pending: PendingRegistration, code: str) -> tuple[bool, str | None]:
    if pending.consumed_at or pending.expires_at <= utcnow():
        return False, "Phiên đăng ký đã hết hạn. Hãy quay lại đăng ký."
    if pending.attempts >= MAX_ATTEMPTS:
        return False, "Đã nhập sai 5 lần. Hãy yêu cầu mã mới."
    if not pending.code_hash or not pending.code_expires_at or pending.code_expires_at <= utcnow():
        return False, "Mã đã hết hạn hoặc chưa được gửi. Hãy yêu cầu mã mới."
    pending.attempts += 1
    expected = digest("otp:"+pending.id+":"+code)
    if not re.fullmatch(r"[0-9]{6}", code) or not hmac.compare_digest(expected, pending.code_hash):
        return False, f"Mã không đúng. Bạn còn {MAX_ATTEMPTS-pending.attempts} lần nhập."
    return True, None


def purge_expired(db: Session) -> None:
    """Remove pending credentials after expiry; never touches a real account."""
    db.query(PendingRegistration).filter(PendingRegistration.expires_at < utcnow()).delete()
    db.query(PasswordReset).filter(PasswordReset.expires_at < utcnow()-timedelta(days=1)).delete()
    db.query(AuthRateLimit).filter(AuthRateLimit.window_started < utcnow()-timedelta(days=2)).delete()
    db.commit()
