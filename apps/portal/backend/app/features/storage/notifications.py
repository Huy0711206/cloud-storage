"""In-app inbox derived from active invitations and plan status plus completed receipts."""
import hashlib
from datetime import timedelta

from app.core.models import User, utcnow
from app.features.billing.entitlements import benefits_for_user
from .access import fresh_user, scope_guard
from .collaboration_models import Team, TeamMember
from .native_service import StorageError
from .workspace_models import WorkspaceNotice


def record_receipt(db, request, upload_id, file_name):
    db.add(WorkspaceNotice(user_id=request.owner_id, id=f"receipt-{upload_id}",
                           kind="file_received", label=file_name))


def notice_key(kind, value):
    return hashlib.sha256(f"{kind}:{value}".encode()).hexdigest()


def visible_notices(db, user):
    now = utcnow()
    rows = db.query(WorkspaceNotice).filter_by(user_id=user.id, kind="file_received").order_by(
        WorkspaceNotice.created_at.desc(), WorkspaceNotice.id.desc()).limit(50)
    items = [
        dict(id=row.id, kind=row.kind, label=row.label, created_at=row.created_at)
        for row in rows
    ]

    invitations = db.query(TeamMember, Team, User).join(Team, TeamMember.team_id == Team.id).join(
        User, Team.owner_id == User.id
    ).filter(TeamMember.user_id == user.id, TeamMember.status == "pending",
             TeamMember.expires_at > now, User.is_active.is_(True), User.is_verified.is_(True)
    ).order_by(TeamMember.invited_at.desc()).limit(50)
    for invitation, team, owner in invitations:
        if benefits_for_user(owner).get("team_space"):
            key = notice_key("team_invite", f"{invitation.id}:{invitation.invited_at.isoformat()}")
            items.append(dict(id=key, kind="team_invite", label=team.name, created_at=invitation.invited_at))

    expiry = user.plan_expires_at
    if user.plan and user.plan.code != "free" and expiry and now < expiry <= now + timedelta(days=7):
        items.append(dict(id=notice_key("plan_expiry", expiry.isoformat()), kind="plan_expiry",
                          label=user.plan.name, created_at=expiry-timedelta(days=7), expires_at=expiry))

    items.sort(key=lambda item: (item["created_at"], item["id"]), reverse=True)
    return items[:50]


def list_notifications(db, user):
    user = fresh_user(db, user.id)
    notices = visible_notices(db, user)
    viewed = {row[0] for row in db.query(WorkspaceNotice.id).filter(
        WorkspaceNotice.user_id == user.id, WorkspaceNotice.id.in_([item["id"] for item in notices]),
        WorkspaceNotice.read_at.is_not(None))}
    for item in notices:
        item["read"] = item["id"] in viewed
        item["created_at"] = item["created_at"].isoformat() + "Z"
        if "expires_at" in item:
            item["expires_at"] = item["expires_at"].isoformat() + "Z"
    return {"items": notices, "unread": sum(not item["read"] for item in notices)}


def mark_read(db, user, key):
    with scope_guard(db, user) as (owner, _, _):
        current = next((item for item in visible_notices(db, owner) if item["id"] == key), None)
        if current is None:
            raise StorageError(404, "Không tìm thấy thông báo.")
        row = db.get(WorkspaceNotice, (owner.id, key))
        if row is None:
            row = WorkspaceNotice(user_id=owner.id, id=key, kind=current["kind"], created_at=current["created_at"])
            db.add(row)
        if row.read_at is None:
            row.read_at = utcnow()
        db.commit()
    return {"ok": True}
