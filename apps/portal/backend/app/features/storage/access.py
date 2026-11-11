"""Authoritative personal/team/inbox scope rules; callers never supply a sponsor role."""
from contextlib import contextmanager
import hashlib
from app.core.models import User, Plan, utcnow
from app.features.billing.entitlements import require_feature
from .native_models import FileNode
from .collaboration_models import Team, TeamMember, FileRequest


def fresh_user(db, user_id):
    from .native_service import StorageError
    user = db.query(User).filter_by(id=user_id).populate_existing().first()
    if not user:
        raise StorageError(401, "Vui lòng đăng nhập.")
    if not user.is_active or not user.is_verified:
        raise StorageError(403, "Tài khoản chưa được xác minh hoặc đã bị khóa.")
    db.expire(user,["plan"])
    if user.plan_id is not None:
        db.query(Plan).filter_by(id=user.plan_id).populate_existing().first()
    return user


def team_node_ids(db, owner_id):
    from . import native_service as s
    result = set()
    for team in db.query(Team).filter_by(owner_id=owner_id).populate_existing():
        root = db.query(FileNode).filter_by(id=team.root_id).populate_existing().first()
        if root:
            result.update(n.id for n in s.descendants(db, root, True))
    return result


def assert_personal_node(db, owner_id, node_id):
    from . import native_service as s
    if not node_id:
        return
    roots = {row[0] for row in db.query(Team.root_id).filter_by(owner_id=owner_id)}
    cursor = s.owned_node(db, owner_id, node_id, True)
    seen = set()
    while cursor:
        if cursor.id in roots or cursor.id in seen:
            raise s.StorageError(404, "Không tìm thấy tệp trong kho cá nhân.")
        seen.add(cursor.id)
        cursor = s.owned_node(db, owner_id, cursor.parent_id, True) if cursor.parent_id else None


def personal_node(db, user, node_id, deleted=False):
    from . import native_service as s
    user = fresh_user(db, user.id)
    assert_personal_node(db, user.id, node_id)
    return s.owned_node(db, user.id, node_id, deleted)


def team_access(db, user, team_id, write=False, owner_only=False):
    from .native_service import StorageError
    user = fresh_user(db, user.id)
    team = db.query(Team).filter_by(id=team_id).populate_existing().first()
    if not team:
        raise StorageError(404, "Không tìm thấy không gian nhóm.")
    try:
        sponsor = fresh_user(db, team.owner_id)
    except StorageError:
        raise StorageError(404, "Không gian nhóm không còn khả dụng.")
    if user.id == sponsor.id:
        role = "owner"
    else:
        member = db.query(TeamMember).filter_by(team_id=team.id, user_id=user.id, status="active").populate_existing().first()
        if not member:
            raise StorageError(404, "Không tìm thấy không gian nhóm.")
        role = member.role
    if owner_only and role != "owner":
        raise StorageError(403, "Chỉ chủ nhóm được quản lý thành viên.")
    if write:
        require_feature(sponsor, "team_space")
        if role not in ("owner", "editor"):
            raise StorageError(403, "Bạn chỉ có quyền xem trong nhóm.")
    return team, sponsor, role


def team_node(db, team, node_id=None, deleted=False):
    from . import native_service as s
    root = s.owned_node(db, team.owner_id, team.root_id)
    node = s.owned_node(db, team.owner_id, node_id or root.id, deleted)
    cursor = node
    seen = set()
    while cursor:
        if cursor.id == root.id:
            return node
        if cursor.id in seen:
            break
        seen.add(cursor.id)
        cursor = s.owned_node(db, team.owner_id, cursor.parent_id, deleted) if cursor.parent_id else None
    raise s.StorageError(404, "Tệp không thuộc không gian nhóm này.")


def request_access(db, token, allow_closed=False):
    from . import native_service as s
    if len(token) > 256:
        raise s.StorageError(404, "Yêu cầu không khả dụng.")
    row = db.query(FileRequest).filter_by(token_hash=hashlib.sha256(token.encode()).hexdigest()).populate_existing().first()
    if not row:
        raise s.StorageError(404, "Yêu cầu không khả dụng.")
    try:
        owner = fresh_user(db, row.owner_id)
    except s.StorageError:
        raise s.StorageError(404, "Yêu cầu không khả dụng.")
    if not allow_closed:
        require_feature(owner, "file_requests")
        if row.closed_at or row.expires_at <= utcnow() or not row.parent_id:
            raise s.StorageError(410, "Yêu cầu nhận tệp đã đóng hoặc hết hạn.")
        assert_personal_node(db, owner.id, row.parent_id)
        s.parent_folder(db, owner.id, row.parent_id)
    return row, owner


@contextmanager
def scope_guard(db, actor, *, team_id=None, request_token=None, write=False, allow_closed=False):
    from . import native_service as s
    if team_id is not None and request_token is not None:
        raise s.StorageError(400, "Phạm vi thao tác không hợp lệ.")
    if request_token is not None:
        request, owner = request_access(db, request_token, allow_closed)
    elif team_id is not None:
        _, owner, _ = team_access(db, actor, team_id)
    else:
        owner = fresh_user(db, actor.id)
    with s.owner_guard(db, owner.id, actor_id=actor.id if actor is not None else None):
        if request_token is not None:
            request, owner = request_access(db, request_token, allow_closed)
            yield owner, None, request
        elif team_id is not None:
            team, owner, _ = team_access(db, actor, team_id, write=write)
            yield owner, team, None
        else:
            yield fresh_user(db, actor.id), None, None


@contextmanager
def team_guard(db, actor, team_id, write=False, owner_only=False):
    with scope_guard(db, actor, team_id=team_id, write=write) as (owner, team, _):
        _, _, role = team_access(db, actor, team_id, write, owner_only)
        yield team, owner, role


def scoped_node(db, owner, team, node_id, deleted=False, mutable=False):
    from . import native_service as s
    if team:
        node = team_node(db, team, node_id, deleted)
        if mutable and node.id == team.root_id:
            raise s.StorageError(400, "Không thể thay đổi thư mục gốc của nhóm.")
        return node
    assert_personal_node(db, owner.id, node_id)
    return s.owned_node(db, owner.id, node_id, deleted)


def scoped_parent(db, owner, team, parent_id):
    from . import native_service as s
    if parent_id is None and team is None:
        return None
    parent = scoped_node(db, owner, team, parent_id)
    if not parent.is_folder:
        raise s.StorageError(400, "Vị trí đích phải là thư mục.")
    return parent.id
