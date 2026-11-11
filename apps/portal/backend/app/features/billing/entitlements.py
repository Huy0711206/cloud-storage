"""Single source for shipped plan benefits; storage rechecks effective expiry per request."""
from app.core.models import utcnow

BENEFITS = {
    "free": dict(version_days=0, expiring_links=False, password_links=False, file_requests=False, team_space=False, share_stats=False, team_members=0),
    "basic": dict(version_days=30, expiring_links=True, password_links=False, file_requests=False, team_space=False, share_stats=False, team_members=0),
    "standard": dict(version_days=90, expiring_links=True, password_links=True, file_requests=True, team_space=False, share_stats=False, team_members=0),
    "premium": dict(version_days=180, expiring_links=True, password_links=True, file_requests=True, team_space=True, share_stats=True, team_members=5),
}

def effective_plan(user):
    plan = user.plan
    if not plan:
        return None
    if plan.price_vnd > 0 and user.plan_expires_at is not None and user.plan_expires_at <= utcnow():
        return None
    return plan


def benefits_for_code(code):
    code = code if code in BENEFITS else "free"
    return {"code": code, **BENEFITS[code], "versions": BENEFITS[code]["version_days"] > 0}


def benefits_for_user(user):
    plan = effective_plan(user)
    return benefits_for_code(plan.code if plan else "free")


def require_feature(user, feature):
    from app.features.storage.native_service import StorageError
    benefits = benefits_for_user(user)
    if not user.is_active or not user.is_verified or not benefits.get(feature):
        raise StorageError(403, "Gói hiện tại chưa có tính năng này hoặc đã hết hạn. Hãy xem quyền lợi gói dịch vụ.")
    return benefits
