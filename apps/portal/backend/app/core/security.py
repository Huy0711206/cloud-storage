import hashlib
import hmac
import os

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from .config import settings

_SCRYPT = dict(n=2**14, r=8, p=1, dklen=32)


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, **_SCRYPT)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, salt_hex, digest_hex = stored.split("$")
        if scheme != "scrypt":
            return False
        digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), **_SCRYPT)
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.secret_key, salt="verify-email")


def make_verify_token(email: str) -> str:
    return _serializer().dumps(email)


def read_verify_token(token: str) -> str | None:
    """Trả về email nếu token hợp lệ và chưa hết hạn, ngược lại None."""
    try:
        return _serializer().loads(token, max_age=settings.verify_token_max_age)
    except (BadSignature, SignatureExpired):
        return None
