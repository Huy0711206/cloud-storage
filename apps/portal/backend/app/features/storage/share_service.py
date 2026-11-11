"""Protected links, session-scoped unlocks and aggregate (not unique-viewer) counts."""
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets

from app.core.config import settings
from app.core.models import User, utcnow
from app.core.security import hash_password, verify_password
from app.features.authentication.otp import consume_rate, digest
from app.features.billing.entitlements import benefits_for_user, require_feature
from . import native_service as s
from .native_models import FileShare
from .share_models import ShareProtection, ShareStatistics
from .access import scope_guard, scoped_node, assert_personal_node


def lookup(db, token):
    if len(token) > 256:
        raise s.StorageError(404, "Liên kết không hợp lệ hoặc đã bị thu hồi.")
    row = db.query(FileShare).filter_by(token_hash=hashlib.sha256(token.encode()).hexdigest(), revoked_at=None).first()
    if not row or (row.expires_at and row.expires_at <= utcnow()):
        raise s.StorageError(404, "Liên kết không hợp lệ, đã hết hạn hoặc đã bị thu hồi.")
    owner = db.get(User, row.owner_id)
    if not owner or not owner.is_active or not owner.is_verified:
        raise s.StorageError(404, "Liên kết không còn khả dụng.")
    assert_personal_node(db,owner.id,row.node_id)
    s.owned_node(db, owner.id, row.node_id)
    return row


def fingerprint(protection):
    return digest("share-unlock:" + protection.share_id + ":" + protection.password_hash)


def authorize(db, token, session=None):
    share = lookup(db, token)
    protection = db.get(ShareProtection, share.id)
    if protection and protection.password_hash:
        grant = (session or {}).get("share_grants", {}).get(share.id, {})
        if not isinstance(grant, dict) or grant.get("until", 0) <= utcnow().timestamp() or not hmac.compare_digest(str(grant.get("proof", "")), fingerprint(protection)):
            raise s.StorageError(401, "Liên kết này cần mật khẩu. Hãy mở trang chia sẻ để nhập mật khẩu.")
    return share


def unlock(db, token, password, session, source):
    share = lookup(db, token)
    with s.owner_guard(db, share.owner_id):
        share = lookup(db, token)
        # Stored HMAC keys retain neither IP address nor the share token.
        allowed = consume_rate(db, "share-password:" + share.id, 20)
        source_allowed = consume_rate(db, "share-password-source:" + source, 60)
        db.commit()  # Invalid attempts must persist despite the 401/429 response.
        if not allowed or not source_allowed:
            raise s.StorageError(429, "Đã thử mật khẩu quá nhiều lần. Hãy thử lại sau một giờ.")
        share = lookup(db,token)
        protection = db.query(ShareProtection).filter_by(share_id=share.id).populate_existing().first()
        if protection and protection.password_hash:
            if not verify_password(password, protection.password_hash):
                raise s.StorageError(401, "Mật khẩu liên kết chưa đúng.")
            grants = {key: value for key, value in session.get("share_grants", {}).items() if isinstance(value, dict) and value.get("until", 0) > utcnow().timestamp()}
            # Bound the signed session cookie; no plaintext password/hash is stored in it.
            while len(grants) >= 8:
                grants.pop(next(iter(grants)))
            grants[share.id] = {"proof": fingerprint(protection), "until": (utcnow() + timedelta(hours=1)).timestamp()}
            session["share_grants"] = grants


def parse_expiry(value):
    if not value:
        return None
    try:
        date = datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value
        if date.tzinfo is None:
            raise ValueError()
        date = date.astimezone(timezone.utc).replace(tzinfo=None)
    except (ValueError, TypeError, AttributeError):
        raise s.StorageError(400, "Hạn dùng phải là thời điểm có múi giờ rõ ràng.")
    if not utcnow() < date <= utcnow() + timedelta(days=365):
        raise s.StorageError(400, "Hạn dùng phải trong tương lai và không quá 365 ngày.")
    return date


def create(db, user, node_id, expires_at=None, password=None):
    with scope_guard(db,user,write=True) as (user,_,__):
        node = scoped_node(db,user,None,node_id)
        if expires_at:
            require_feature(user, "expiring_links")
        if password:
            require_feature(user, "password_links")
            if not 8 <= len(password) <= 128:
                raise s.StorageError(400, "Mật khẩu liên kết cần từ 8 đến 128 ký tự.")
        token = secrets.token_urlsafe(32)
        share = FileShare(owner_id=user.id, node_id=node.id, token_hash=hashlib.sha256(token.encode()).hexdigest(), expires_at=parse_expiry(expires_at))
        db.add(share)
        db.flush()
        if password:
            db.add(ShareProtection(share_id=share.id, password_hash=hash_password(password)))
        db.commit()
        return {"id": share.id, "token": token, "url": settings.base_url + "/s/" + token, "permission": "read", "expires_at": share.expires_at.isoformat()+"Z" if share.expires_at else None, "password_protected": bool(password)}


def metadata(db, user, share):
    protection = db.get(ShareProtection, share.id)
    result = {"expires_at": share.expires_at.isoformat()+"Z" if share.expires_at else None, "password_protected": bool(protection and protection.password_hash)}
    if benefits_for_user(user)["share_stats"]:
        stats = db.get(ShareStatistics, share.id)
        result.update(views=stats.views if stats else 0, downloads=stats.downloads if stats else 0, stats_since=stats.started_at.isoformat()+"Z" if stats else None)
    return result


def record(db, share_id, event):
    share = db.get(FileShare, share_id)
    if not share:
        return
    with s.owner_guard(db, share.owner_id):
        if not benefits_for_user(db.get(User, share.owner_id))["share_stats"]:
            return
        row = db.get(ShareStatistics, share.id)
        if not row:
            row = ShareStatistics(share_id=share.id, views=0, downloads=0)
            db.add(row)
        if event == "view":
            row.views += 1
        elif event == "download":
            row.downloads += 1
        db.commit()
