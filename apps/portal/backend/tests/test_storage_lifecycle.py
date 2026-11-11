"""Upload lifecycle contracts across personal, team and upload-only namespaces.

All cases use disposable SQLite metadata and real temporary files. SQLAlchemy
events inject transaction failures without replacing the storage implementation.
"""
from datetime import timedelta

import pytest
from sqlalchemy import event

from app.core.models import Plan, User, utcnow
from app.features.storage import native_service as storage
from app.features.storage import request_service as requests
from app.features.storage import team_service as teams
from app.features.storage.collaboration_models import FileRequest, RequestUpload, Team, TeamUpload
from app.features.storage.migration_models import FileVersion
from app.features.storage.native_models import FileNode, UploadSession
from app.features.storage.version_routes import router as personal_versions
from test_collaboration_features import env, folder, join, request, team


SCOPES = ("personal", "team", "request")


@pytest.fixture(autouse=True)
def isolated_pool(monkeypatch):
    monkeypatch.setenv("STORAGE_POOL_LIMIT_BYTES", "0")


def namespace(client, scope):
    if scope == "team":
        row = team(client)
        return f'/api/teams/{row["id"]}/uploads'
    if scope == "request":
        _, token = request(client)
        return f"/api/requests/{token}/uploads"
    return "/api/uploads"


def start(client, base, data=b"payload", name="payload.bin", **extra):
    response = client.post(base, json={"name": name, "size": len(data), **extra})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def append(client, base, upload_id, data=b"payload", offset=0):
    response = client.put(
        f"{base}/{upload_id}", content=data, headers={"Upload-Offset": str(offset)}
    )
    assert response.status_code == 200, response.text
    return response


def send(client, base, data, name="payload.bin", **extra):
    upload_id = start(client, base, data, name, **extra)
    append(client, base, upload_id, data)
    response = client.post(f"{base}/{upload_id}/complete")
    assert response.status_code == 200, response.text
    return response.json(), upload_id


@pytest.mark.parametrize("scope,binding", [("team", TeamUpload), ("request", RequestUpload)])
def test_start_binding_failure_rolls_back_reservation_and_temporary_file(env, scope, binding):
    client, factory = env
    base = namespace(client, scope)

    def fail_binding(session, *_):
        if any(isinstance(row, binding) for row in session.new):
            raise RuntimeError("injected upload binding failure")

    event.listen(factory.class_, "before_flush", fail_binding)
    try:
        with pytest.raises(RuntimeError, match="injected upload binding failure"):
            client.post(base, json={"name": "atomic.bin", "size": 7})
    finally:
        event.remove(factory.class_, "before_flush", fail_binding)

    with factory() as db:
        assert db.query(UploadSession).count() == 0
        assert db.query(binding).count() == 0
        assert storage.quota_usage(db, db.get(User, 1))["reserved"] == 0
    assert not any(path.is_file() for path in storage.storage_root().rglob("*"))
    # Rollback must leave the same public operation usable on the next request.
    assert client.post(base, json={"name": "atomic.bin", "size": 7}).status_code == 201


@pytest.mark.parametrize("scope", SCOPES)
def test_start_commit_failure_does_not_leave_unbound_rows_or_files(env, scope):
    client, factory = env
    base = namespace(client, scope)
    created = []

    def fail_start_commit(session):
        pending = [row for row in session.identity_map.values()
                   if isinstance(row, UploadSession) and row.state == "pending"]
        if pending:
            assert len(pending) == 1
            assert storage.upload_path(pending[0].id).is_file()
            created.append(pending[0].id)
            raise RuntimeError("injected start commit failure")

    event.listen(factory.class_, "before_commit", fail_start_commit)
    try:
        with pytest.raises(RuntimeError, match="injected start commit failure"):
            client.post(base, json={"name": "uncommitted.bin", "size": 7})
    finally:
        event.remove(factory.class_, "before_commit", fail_start_commit)
    assert len(created) == 1
    with factory() as db:
        assert db.query(UploadSession).count() == 0
        assert db.query(TeamUpload).count() == 0
        assert db.query(RequestUpload).count() == 0
        assert storage.quota_usage(db, db.get(User, 1))["reserved"] == 0
    assert not storage.upload_path(created[0]).exists()
    assert not storage.blob_path(created[0]).exists()


def assert_binding(db, scope, upload_id):
    group = db.get(TeamUpload, upload_id)
    inbox = db.get(RequestUpload, upload_id)
    if scope == "team":
        assert group is not None and inbox is None
        assert group.team_id == db.query(Team).one().id
        assert group.user_id == 1
    elif scope == "request":
        assert inbox is not None and group is None
        assert inbox.request_id == db.query(FileRequest).one().id
    else:
        assert group is None and inbox is None


@pytest.mark.parametrize("scope", SCOPES)
def test_lost_start_commit_acknowledgement_preserves_bound_resumable_session(env, monkeypatch, scope):
    client, factory = env
    base = namespace(client, scope)
    real_commit = factory.class_.commit
    lost = []

    def commit_then_lose_ack(session):
        pending = [row for row in session.identity_map.values() if isinstance(row, UploadSession)
                   and row.name == "lost-start.bin" and row.state == "pending"]
        target = pending[0].id if pending and not lost else None
        real_commit(session)
        if target is not None:
            lost.append(target)
            raise RuntimeError("injected lost start commit acknowledgement")

    monkeypatch.setattr(factory.class_, "commit", commit_then_lose_ack)
    with pytest.raises(RuntimeError, match="injected lost start commit acknowledgement"):
        client.post(base, json={"name": "lost-start.bin", "size": 7})
    assert len(lost) == 1
    # Recover the ID from durable metadata because the original response was lost.
    with factory() as db:
        row = db.query(UploadSession).one()
        upload_id = row.id
        assert upload_id == lost[0]
        assert (row.owner_id, row.state, row.received, row.size) == (1, "pending", 0, 7)
        assert_binding(db, scope, upload_id)
        assert db.query(FileNode).filter_by(is_folder=False).count() == 0
        assert storage.quota_usage(db, db.get(User, 1))["reserved"] == 7
    assert storage.upload_path(upload_id).read_bytes() == b""
    assert not storage.blob_path(upload_id).exists()
    append(client, base, upload_id)
    response = client.post(f"{base}/{upload_id}/complete")
    assert response.status_code == 200, response.text
    with factory() as db:
        row = db.get(UploadSession, upload_id)
        assert row.state == "complete"
        assert_binding(db, scope, upload_id)
        assert storage.blob_path(db.get(FileNode, row.node_id).blob_key).read_bytes() == b"payload"
        assert storage.quota_usage(db, db.get(User, 1))["reserved"] == 0


@pytest.mark.parametrize("scope", SCOPES)
def test_lost_finish_commit_acknowledgement_keeps_completed_blob_and_retries_safe(env, monkeypatch, scope):
    client, factory = env
    base = namespace(client, scope)
    upload_id = start(client, base)
    append(client, base, upload_id)
    real_commit = factory.class_.commit
    lost = []

    def commit_then_lose_ack(session):
        completing = any(isinstance(row, UploadSession) and row.id == upload_id and row.state == "complete"
                         for row in session.identity_map.values())
        target = completing and not lost
        real_commit(session)
        if target:
            lost.append(upload_id)
            raise RuntimeError("injected lost finish commit acknowledgement")

    monkeypatch.setattr(factory.class_, "commit", commit_then_lose_ack)
    with pytest.raises(RuntimeError, match="injected lost finish commit acknowledgement"):
        client.post(f"{base}/{upload_id}/complete")
    assert lost == [upload_id]
    with factory() as db:
        row = db.get(UploadSession, upload_id)
        assert (row.state, row.received) == ("complete", 7)
        assert_binding(db, scope, upload_id)
        node = db.get(FileNode, row.node_id)
        node_id = node.id
        assert node.blob_key == upload_id
        assert storage.blob_path(node.blob_key).read_bytes() == b"payload"
        expected = {"ok": True, "name": "payload.bin", "size": 7} if scope == "request" else storage.serialize_node(node)
        usage = storage.quota_usage(db, db.get(User, 1))
        assert (usage["used"], usage["reserved"]) == (7, 0)
    assert not storage.upload_path(upload_id).exists()
    for _ in range(2):
        response = client.post(f"{base}/{upload_id}/complete")
        assert response.status_code == 200, response.text
        assert response.json() == expected
        assert client.delete(f"{base}/{upload_id}").json() == {"ok": True}
        assert storage.blob_path(upload_id).read_bytes() == b"payload"
    with factory() as db:
        assert db.get(UploadSession, upload_id).node_id == node_id
        assert db.query(FileNode).filter_by(is_folder=False).count() == 1
        assert db.query(FileVersion).count() == 0


@pytest.mark.parametrize("scope", ["team", "request"])
@pytest.mark.parametrize("action", ["chunk", "complete", "abort"])
@pytest.mark.parametrize("completed", [False, True], ids=["pending", "completed"])
def test_personal_upload_actions_reject_every_bound_upload_id(env, scope, action, completed):
    client, factory = env
    base = namespace(client, scope)
    upload_id = start(client, base)
    append(client, base, upload_id)
    if completed:
        assert client.post(f"{base}/{upload_id}/complete").status_code == 200

    path = f"/api/uploads/{upload_id}"
    if action == "chunk":
        response = client.put(path, content=b"", headers={"Upload-Offset": "7"})
    elif action == "complete":
        response = client.post(path + "/complete")
    else:
        response = client.delete(path)
    assert response.status_code == 404, response.text

    with factory() as db:
        row = db.get(UploadSession, upload_id)
        assert row.state == ("complete" if completed else "pending")
        assert row.received == 7
        if completed:
            assert storage.blob_path(db.get(FileNode, row.node_id).blob_key).read_bytes() == b"payload"
        else:
            assert storage.upload_path(upload_id).read_bytes() == b"payload"


@pytest.mark.parametrize("scope", ["team", "request"])
@pytest.mark.parametrize("action", ["chunk", "complete", "abort"])
def test_native_personal_interface_cannot_adopt_bound_upload_ids(env, scope, action):
    client, factory = env
    base = namespace(client, scope)
    upload_id = start(client, base)
    append(client, base, upload_id)
    with factory() as db:
        owner = db.get(User, 1)
        with pytest.raises(storage.StorageError) as denied:
            if action == "chunk":
                storage.append_chunk(db, owner, upload_id, b"", 7)
            elif action == "complete":
                storage.finish_upload(db, owner, upload_id)
            else:
                storage.abort_upload(db, owner, upload_id)
        assert denied.value.status == 404
    with factory() as db:
        assert db.get(UploadSession, upload_id).state == "pending"
        assert db.query(FileNode).filter_by(is_folder=False).count() == 0
    assert storage.upload_path(upload_id).read_bytes() == b"payload"


@pytest.mark.parametrize("action", ["chunk", "complete", "abort"])
def test_membership_revocation_prevents_inflight_upload_actions(env, action):
    client, factory = env
    row = team(client)
    join(client, row)
    base = f'/api/teams/{row["id"]}/uploads'
    upload_id = start(client, base)
    append(client, base, upload_id)
    client.headers["x-user"] = "1"
    assert client.delete(f'/api/teams/{row["id"]}/members/2').status_code == 200
    client.headers["x-user"] = "2"
    if action == "chunk":
        response = client.put(f"{base}/{upload_id}", content=b"", headers={"Upload-Offset": "7"})
    elif action == "complete":
        response = client.post(f"{base}/{upload_id}/complete")
    else:
        response = client.delete(f"{base}/{upload_id}")
    assert response.status_code == 404, response.text
    with factory() as db:
        assert db.get(UploadSession, upload_id).state == "pending"
        assert db.query(FileNode).filter_by(is_folder=False).count() == 0
        db.get(UploadSession, upload_id).expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
        assert storage.expire_uploads(db, 1) == 1
        db.commit()
    assert not storage.upload_path(upload_id).exists()


@pytest.mark.parametrize("attribute", ["is_active", "is_verified"])
@pytest.mark.parametrize("action", ["chunk", "complete", "abort"])
def test_cached_team_actor_is_refreshed_before_upload_action(env, attribute, action):
    client, factory = env
    row = team(client)
    join(client, row)
    base = f'/api/teams/{row["id"]}/uploads'
    upload_id = start(client, base)
    append(client, base, upload_id)
    # A long-lived caller may already have loaded this actor in its identity map.
    with factory() as cached:
        actor = cached.get(User, 2)
        assert getattr(actor, attribute)
        with factory() as other:
            setattr(other.get(User, 2), attribute, False)
            other.commit()
        with pytest.raises(storage.StorageError) as denied:
            teams.team_upload_action(cached, actor, row["id"], upload_id, action, b"", 7)
        assert denied.value.status == 403
    with factory() as db:
        assert db.get(UploadSession, upload_id).state == "pending"
        assert db.query(FileNode).filter_by(is_folder=False).count() == 0
    assert storage.upload_path(upload_id).read_bytes() == b"payload"


@pytest.mark.parametrize("scope", SCOPES)
@pytest.mark.parametrize("limit,status", [("quota", 413), ("pool", 507)])
def test_pending_completion_checks_current_limits_without_losing_bytes(env, monkeypatch, scope, limit, status):
    client, factory = env
    base = namespace(client, scope)
    upload_id = start(client, base)
    append(client, base, upload_id)
    if limit == "quota":
        with factory() as db:
            db.query(Plan).filter_by(code="premium").one().quota_gb = 0
            db.commit()
    else:
        monkeypatch.setenv("STORAGE_POOL_LIMIT_BYTES", "6")
    response = client.post(f"{base}/{upload_id}/complete")
    assert response.status_code == status, response.text
    with factory() as db:
        assert db.get(UploadSession, upload_id).state == "pending"
        assert db.query(FileNode).filter_by(is_folder=False).count() == 0
        assert storage.quota_usage(db, db.get(User, 1))["reserved"] == 7
    assert storage.upload_path(upload_id).read_bytes() == b"payload"
    assert not storage.blob_path(upload_id).exists()
    if limit == "quota":
        with factory() as db:
            db.query(Plan).filter_by(code="premium").one().quota_gb = 2048
            db.commit()
    else:
        monkeypatch.setenv("STORAGE_POOL_LIMIT_BYTES", "0")
    assert client.post(f"{base}/{upload_id}/complete").status_code == 200


@pytest.mark.parametrize("scope", SCOPES)
def test_completed_retry_and_abort_never_duplicate_or_remove_committed_content(env, monkeypatch, scope):
    client, factory = env
    base = namespace(client, scope)
    result, upload_id = send(client, base, b"payload")
    with factory() as db:
        db.query(Plan).filter_by(code="premium").one().quota_gb = 0
        db.commit()
    monkeypatch.setenv("STORAGE_POOL_LIMIT_BYTES", "1")
    for _ in range(2):
        response = client.post(f"{base}/{upload_id}/complete")
        assert response.status_code == 200, response.text
        assert response.json() == result
        assert client.delete(f"{base}/{upload_id}").json() == {"ok": True}
    with factory() as db:
        upload = db.get(UploadSession, upload_id)
        assert upload.state == "complete"
        assert db.query(FileNode).filter_by(is_folder=False).count() == 1
        assert db.query(FileVersion).count() == 0
        assert storage.quota_usage(db, db.get(User, 1))["used"] == 7
        assert storage.quota_usage(db, db.get(User, 1))["reserved"] == 0
        assert storage.blob_path(db.get(FileNode, upload.node_id).blob_key).read_bytes() == b"payload"


@pytest.mark.parametrize("scope", SCOPES)
def test_metadata_commit_failure_after_blob_move_can_be_retried(env, scope):
    client, factory = env
    base = namespace(client, scope)
    upload_id = start(client, base)
    append(client, base, upload_id)
    observed_move = []

    def fail_completion(session):
        if any(isinstance(row, UploadSession) and row.id == upload_id and row.state == "complete"
               for row in session.identity_map.values()):
            assert storage.blob_path(upload_id).read_bytes() == b"payload"
            assert not storage.upload_path(upload_id).exists()
            observed_move.append(True)
            raise RuntimeError("injected metadata commit failure")

    event.listen(factory.class_, "before_commit", fail_completion)
    try:
        with pytest.raises(RuntimeError, match="injected metadata commit failure"):
            client.post(f"{base}/{upload_id}/complete")
    finally:
        event.remove(factory.class_, "before_commit", fail_completion)
    assert observed_move == [True]
    with factory() as db:
        row = db.get(UploadSession, upload_id)
        assert (row.state, row.received, row.node_id) == ("pending", 7, None)
        assert db.query(FileNode).filter_by(is_folder=False).count() == 0
        assert storage.quota_usage(db, db.get(User, 1))["reserved"] == 7
    sources = [path for path in (storage.upload_path(upload_id), storage.blob_path(upload_id)) if path.exists()]
    assert len(sources) == 1
    assert sources[0].read_bytes() == b"payload"
    response = client.post(f"{base}/{upload_id}/complete")
    assert response.status_code == 200, response.text
    with factory() as db:
        row = db.get(UploadSession, upload_id)
        assert row.state == "complete"
        assert storage.blob_path(db.get(FileNode, row.node_id).blob_key).read_bytes() == b"payload"
    assert not storage.upload_path(upload_id).exists()


@pytest.mark.parametrize("scope", ["personal", "team"])
def test_failed_replacement_commit_retains_current_and_archives_once_on_retry(env, scope):
    client, factory = env
    base = namespace(client, scope)
    node, _ = send(client, base, b"original", "revision.txt")
    with factory() as db:
        original_key = db.get(FileNode, node["id"]).blob_key
    upload_id = start(client, base, b"replacement", "revision.txt", replace_node_id=node["id"])
    append(client, base, upload_id, b"replacement")
    observed_move = []

    def fail_replacement_commit(session):
        if any(isinstance(row, UploadSession) and row.id == upload_id and row.state == "complete"
               for row in session.identity_map.values()):
            assert storage.blob_path(upload_id).read_bytes() == b"replacement"
            observed_move.append(True)
            raise RuntimeError("injected replacement commit failure")

    event.listen(factory.class_, "before_commit", fail_replacement_commit)
    try:
        with pytest.raises(RuntimeError, match="injected replacement commit failure"):
            client.post(f"{base}/{upload_id}/complete")
    finally:
        event.remove(factory.class_, "before_commit", fail_replacement_commit)
    assert observed_move == [True]
    with factory() as db:
        current = db.get(FileNode, node["id"])
        assert (current.blob_key, current.size) == (original_key, 8)
        assert storage.blob_path(current.blob_key).read_bytes() == b"original"
        assert db.query(FileVersion).filter_by(node_id=node["id"]).count() == 0
        assert db.get(UploadSession, upload_id).state == "pending"
        usage = storage.quota_usage(db, db.get(User, 1))
        assert (usage["used"], usage["reserved"]) == (8, 11)
    response = client.post(f"{base}/{upload_id}/complete")
    assert response.status_code == 200, response.text
    assert response.json()["id"] == node["id"]
    assert client.post(f"{base}/{upload_id}/complete").json() == response.json()
    with factory() as db:
        version = db.query(FileVersion).filter_by(node_id=node["id"]).one()
        assert version.blob_key == original_key
        assert storage.blob_path(version.blob_key).read_bytes() == b"original"
        assert storage.blob_path(db.get(FileNode, node["id"]).blob_key).read_bytes() == b"replacement"
        usage = storage.quota_usage(db, db.get(User, 1))
        assert (usage["used"], usage["reserved"], usage["versions_used"]) == (19, 0, 8)


@pytest.mark.parametrize("scope", SCOPES)
def test_chunk_metadata_failure_repairs_uncommitted_tail_on_retry(env, scope):
    client, factory = env
    base = namespace(client, scope)
    upload_id = start(client, base)

    def fail_chunk_commit(session):
        if any(isinstance(row, UploadSession) and row.id == upload_id and row.received == 7
               and row.state == "pending" for row in session.identity_map.values()):
            assert storage.upload_path(upload_id).read_bytes() == b"payload"
            raise RuntimeError("injected chunk commit failure")

    event.listen(factory.class_, "before_commit", fail_chunk_commit)
    try:
        with pytest.raises(RuntimeError, match="injected chunk commit failure"):
            client.put(f"{base}/{upload_id}", content=b"payload", headers={"Upload-Offset": "0"})
    finally:
        event.remove(factory.class_, "before_commit", fail_chunk_commit)
    with factory() as db:
        assert db.get(UploadSession, upload_id).received == 0
    append(client, base, upload_id)
    assert client.post(f"{base}/{upload_id}/complete").status_code == 200
    assert storage.blob_path(upload_id).read_bytes() == b"payload"


@pytest.mark.parametrize("scope", SCOPES)
def test_abort_and_expiry_are_repeatable_and_release_reservations(env, scope):
    client, factory = env
    base = namespace(client, scope)
    aborted = start(client, base, name="abort.bin")
    append(client, base, aborted, b"pay")
    for _ in range(2):
        assert client.delete(f"{base}/{aborted}").json() == {"ok": True}
    with factory() as db:
        assert db.get(UploadSession, aborted).state == "aborted"
        assert storage.quota_usage(db, db.get(User, 1))["reserved"] == 0
    assert not storage.upload_path(aborted).exists()
    assert not storage.blob_path(aborted).exists()

    expired = start(client, base, name="expire.bin")
    append(client, base, expired)
    with factory() as db:
        db.get(UploadSession, expired).expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
    assert client.post(f"{base}/{expired}/complete").status_code == 409
    with factory() as db:
        assert storage.expire_uploads(db, 1) == 1
        db.commit()
        assert storage.expire_uploads(db, 1) == 0
        db.commit()
        assert db.get(UploadSession, expired).state == "expired"
        assert storage.quota_usage(db, db.get(User, 1))["reserved"] == 0
    assert client.delete(f"{base}/{expired}").json() == {"ok": True}
    assert not storage.upload_path(expired).exists()
    assert not storage.blob_path(expired).exists()


def test_disabled_owner_still_allows_trusted_expiry_cleanup(env):
    client, factory = env
    temporary = start(client, "/api/uploads", name="temporary.bin")
    append(client, "/api/uploads", temporary)
    renamed = start(client, "/api/uploads", name="renamed.bin")
    append(client, "/api/uploads", renamed)
    destination = storage.blob_path(renamed)
    destination.parent.mkdir(parents=True, exist_ok=True)
    storage.upload_path(renamed).replace(destination)
    with factory() as db:
        db.get(User, 1).is_active = False
        for upload_id in (temporary, renamed):
            db.get(UploadSession, upload_id).expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
        with pytest.raises(storage.StorageError) as denied:
            with storage.owner_guard(db, 1):
                pytest.fail("Disabled user passed authenticated owner guard")
        assert denied.value.status == 403
        with storage.owner_lock(db, 1):
            assert storage.expire_uploads(db, 1) == 2
            db.commit()
        with storage.owner_lock(db, 1):
            assert storage.expire_uploads(db, 1) == 0
            db.commit()
        assert storage.quota_usage(db, db.get(User, 1))["reserved"] == 0
        assert {row.state for row in db.query(UploadSession)} == {"expired"}
    for upload_id in (temporary, renamed):
        assert not storage.upload_path(upload_id).exists()
        assert not storage.blob_path(upload_id).exists()


def restorable_revision(client, scope):
    if scope == "personal":
        client.app.include_router(personal_versions)
    base = namespace(client, scope)
    node, _ = send(client, base, b"original", "restore.txt")
    node, _ = send(client, base, b"current", "restore.txt", replace_node_id=node["id"])
    prefix = "/api" if scope == "personal" else base.rsplit("/uploads", 1)[0]
    versions = f'{prefix}/files/{node["id"]}/versions'
    response = client.get(versions)
    assert response.status_code == 200, response.text
    selected = response.json()["items"][0]["id"]
    assert client.get(f"{versions}/{selected}/download").content == b"original"
    return node["id"], versions, selected


@pytest.mark.parametrize("scope", ["personal", "team"])
def test_failed_restore_commit_keeps_snapshots_and_removes_only_uncommitted_copy(env, scope):
    client, factory = env
    node_id, versions, selected = restorable_revision(client, scope)
    with factory() as db:
        current_key = db.get(FileNode, node_id).blob_key
        selected_key = db.get(FileVersion, selected).blob_key
    copied_keys = []

    def fail_restore_commit(session):
        changed = [row for row in session.identity_map.values() if isinstance(row, FileNode)
                   and row.id == node_id and row.blob_key not in (current_key, selected_key)]
        if changed:
            assert len(changed) == 1
            copied_keys.append(changed[0].blob_key)
            assert storage.blob_path(changed[0].blob_key).read_bytes() == b"original"
            raise RuntimeError("injected restore metadata commit failure")

    event.listen(factory.class_, "before_commit", fail_restore_commit)
    try:
        with pytest.raises(RuntimeError, match="injected restore metadata commit failure"):
            client.post(f"{versions}/{selected}/restore")
    finally:
        event.remove(factory.class_, "before_commit", fail_restore_commit)
    assert len(copied_keys) == 1
    assert not storage.blob_path(copied_keys[0]).exists()
    with factory() as db:
        assert db.get(FileNode, node_id).blob_key == current_key
        assert db.query(FileVersion).filter_by(node_id=node_id).one().id == selected
        assert storage.quota_usage(db, db.get(User, 1))["used"] == 15
    assert storage.blob_path(current_key).read_bytes() == b"current"
    assert storage.blob_path(selected_key).read_bytes() == b"original"
    response = client.post(f"{versions}/{selected}/restore")
    assert response.status_code == 200, response.text
    assert response.json()["item"]["id"] == node_id
    assert client.get(versions.rsplit("/versions", 1)[0] + "/download").content == b"original"
    with factory() as db:
        snapshots = db.query(FileVersion).filter_by(node_id=node_id).all()
        assert {row.blob_key for row in snapshots} == {current_key, selected_key}
        assert storage.quota_usage(db, db.get(User, 1))["used"] == 23


@pytest.mark.parametrize("scope", ["personal", "team"])
def test_lost_restore_commit_acknowledgement_retains_selected_previous_and_current_snapshots(env, monkeypatch, scope):
    client, factory = env
    node_id, versions, selected = restorable_revision(client, scope)
    with factory() as db:
        current_key = db.get(FileNode, node_id).blob_key
        selected_key = db.get(FileVersion, selected).blob_key
    real_commit = factory.class_.commit
    lost = []

    def commit_then_lose_ack(session):
        changed = [row for row in session.identity_map.values() if isinstance(row, FileNode)
                   and row.id == node_id and row.blob_key not in (current_key, selected_key)]
        target = changed[0].blob_key if changed and not lost else None
        real_commit(session)
        if target is not None:
            lost.append(target)
            raise RuntimeError("injected lost restore commit acknowledgement")

    monkeypatch.setattr(factory.class_, "commit", commit_then_lose_ack)
    with pytest.raises(RuntimeError, match="injected lost restore commit acknowledgement"):
        client.post(f"{versions}/{selected}/restore")
    assert len(lost) == 1
    with factory() as db:
        current = db.get(FileNode, node_id)
        assert current.blob_key == lost[0]
        assert current.size == 8
        snapshots = db.query(FileVersion).filter_by(node_id=node_id).all()
        assert {row.blob_key for row in snapshots} == {current_key, selected_key}
        assert db.get(FileVersion, selected).blob_key == selected_key
        assert storage.quota_usage(db, db.get(User, 1))["used"] == 23
    assert storage.blob_path(selected_key).read_bytes() == b"original"
    assert storage.blob_path(current_key).read_bytes() == b"current"
    assert storage.blob_path(lost[0]).read_bytes() == b"original"
    assert client.get(versions.rsplit("/versions", 1)[0] + "/download").content == b"original"
    assert len(client.get(versions).json()["items"]) == 2


def test_replacements_and_versions_cannot_cross_personal_team_namespaces(env):
    client, factory = env
    client.app.include_router(personal_versions)
    group = team(client)
    team_base = f'/api/teams/{group["id"]}/uploads'
    personal, _ = send(client, "/api/uploads", b"personal-old", "same.txt")
    group_file, _ = send(client, team_base, b"team-old", "same.txt")
    personal, personal_upload = send(client, "/api/uploads", b"personal-new", "same.txt", replace_node_id=personal["id"])
    group_file, team_upload = send(client, team_base, b"team-new", "same.txt", replace_node_id=group_file["id"])
    personal_base = f'/api/files/{personal["id"]}/versions'
    group_base = f'/api/teams/{group["id"]}/files/{group_file["id"]}/versions'
    personal_version = client.get(personal_base).json()["items"][0]["id"]
    group_version = client.get(group_base).json()["items"][0]["id"]
    assert client.get(f"{personal_base}/{personal_version}/download").content == b"personal-old"
    assert client.get(f"{group_base}/{group_version}/download").content == b"team-old"

    assert client.post("/api/uploads", json={"name": "same.txt", "size": 1, "replace_node_id": group_file["id"]}).status_code == 404
    assert client.post(team_base, json={"name": "same.txt", "size": 1, "replace_node_id": personal["id"]}).status_code == 404
    for base, alien_version in [(personal_base, group_version), (group_base, personal_version)]:
        assert client.get(f"{base}/{alien_version}/download").status_code == 404
        assert client.post(f"{base}/{alien_version}/restore").status_code == 404
    assert client.get(f'/api/files/{group_file["id"]}/versions').status_code == 404
    assert client.get(f'/api/teams/{group["id"]}/files/{personal["id"]}/versions').status_code == 404
    # Completion retries of replacements archive the previous revision only once.
    assert client.post(f"/api/uploads/{personal_upload}/complete").json() == personal
    assert client.post(f"{team_base}/{team_upload}/complete").json() == group_file
    with factory() as db:
        assert db.query(FileVersion).filter_by(node_id=personal["id"]).count() == 1
        assert db.query(FileVersion).filter_by(node_id=group_file["id"]).count() == 1
    assert client.get(f'/api/files/{personal["id"]}/download').content == b"personal-new"
    assert client.get(f'/api/teams/{group["id"]}/files/{group_file["id"]}/download').content == b"team-new"


def test_nested_team_trash_restore_falls_back_to_team_root(env):
    client, factory = env
    group = team(client)
    base = f'/api/teams/{group["id"]}'
    response = client.post(base + "/folders", json={"name": "Parent"})
    assert response.status_code == 201, response.text
    parent_id = response.json()["id"]
    child, _ = send(client, base + "/uploads", b"retained", parent_id=parent_id)
    assert client.post(f'{base}/files/{child["id"]}/trash').status_code == 200
    assert client.post(f"{base}/files/{parent_id}/trash").status_code == 200
    response = client.post(f'{base}/files/{child["id"]}/restore')
    assert response.status_code == 200, response.text
    with factory() as db:
        restored = db.get(FileNode, child["id"])
        assert restored.parent_id == group["root_id"]
        assert restored.deleted_at is None
        assert db.get(FileNode, parent_id).deleted_at is not None
    assert [item["id"] for item in client.get(base + "/files").json()["items"]] == [child["id"]]
    assert client.get(f'{base}/files/{child["id"]}/download').content == b"retained"
    assert client.get(f'/api/files/{child["id"]}').status_code == 404


def test_shared_personal_root_moved_beneath_team_is_no_longer_public(env):
    client, factory = env
    parent_id = folder(client, "Shared root")
    child, _ = send(client, "/api/uploads", b"private", parent_id=parent_id)
    response = client.post(f"/api/files/{parent_id}/shares")
    assert response.status_code == 201, response.text
    token = response.json()["token"]
    assert client.get(f"/s/{token}").status_code == 200
    assert client.get(f'/s/{token}/download/{child["id"]}').content == b"private"
    group = team(client)
    # Simulate retained metadata whose ancestry changed after the share was issued.
    with factory() as db:
        db.get(FileNode, parent_id).parent_id = group["root_id"]
        db.commit()
    assert client.get(f"/s/{token}").status_code == 404
    assert client.get(f'/s/{token}/download/{child["id"]}').status_code == 404
    assert client.get(f'/api/teams/{group["id"]}/files/{child["id"]}/download').content == b"private"


def test_cached_personal_node_cannot_be_changed_after_ancestry_moves_to_team(env):
    client, factory = env
    item, _ = send(client, "/api/uploads", b"private")
    group = team(client)
    with factory() as cached:
        actor = cached.get(User, 1)
        node = cached.get(FileNode, item["id"])
        assert node.parent_id is None
        with factory() as other:
            other.get(FileNode, item["id"]).parent_id = group["root_id"]
            other.commit()
        with pytest.raises(storage.StorageError) as denied:
            storage.update_node(cached, actor, item["id"], {"name": "adopted.bin"})
        assert denied.value.status == 404
    with factory() as db:
        node = db.get(FileNode, item["id"])
        assert (node.parent_id, node.name) == (group["root_id"], "payload.bin")


def test_cached_plan_quota_is_refreshed_before_completion(env):
    client, factory = env
    upload_id = start(client, "/api/uploads")
    append(client, "/api/uploads", upload_id)
    with factory() as cached:
        actor = cached.get(User, 1)
        plan = actor.plan
        assert plan.quota_gb == 2048
        with factory() as other:
            other.get(Plan, plan.id).quota_gb = 0
            other.commit()
        with pytest.raises(storage.StorageError) as denied:
            storage.finish_upload(cached, actor, upload_id)
        assert denied.value.status == 413
    with factory() as db:
        assert db.get(UploadSession, upload_id).state == "pending"
        assert db.query(FileNode).filter_by(is_folder=False).count() == 0
    assert storage.upload_path(upload_id).read_bytes() == b"payload"


@pytest.mark.parametrize("operation", ["team", "request", "replacement"])
def test_detached_paid_actor_cannot_override_actual_database_free_plan(env, operation):
    client, factory = env
    client.headers["x-user"] = "2"
    parent_id = folder(client, "Free inbox")
    node, _ = send(client, "/api/uploads", b"free", "free.txt", parent_id=parent_id)
    fake_plan = Plan(id=-1, code="premium", name="Forged paid claim", quota_gb=2048, price_vnd=199000)
    actor = User(id=2, email="member2@gmail.com", full_name="Detached claim", password_hash="unused",
                 role="user", is_active=True, is_verified=True, plan=fake_plan,
                 plan_expires_at=utcnow() + timedelta(days=30))
    with factory() as db:
        assert db.get(User, 2).plan.code == "free"
        with pytest.raises(storage.StorageError) as denied:
            if operation == "team":
                teams.create_team(db, actor, "Forbidden premium team")
            elif operation == "request":
                requests.create_request(db, actor, "Forbidden inbox", parent_id, 7, 64, 128)
            else:
                storage.start_upload(db, actor, "free.txt", parent_id, 3, node["id"])
        assert denied.value.status == 403
    with factory() as db:
        assert db.query(Team).filter_by(owner_id=2).count() == 0
        assert db.query(FileRequest).filter_by(owner_id=2).count() == 0
        assert db.query(UploadSession).filter_by(owner_id=2, state="pending").count() == 0
        assert db.get(FileNode, node["id"]).size == 4


def test_trusted_expiry_cleanup_does_not_grant_disabled_actor_access(env):
    client,factory=env
    upload_id=client.post('/api/uploads',json={'name':'abandoned.bin','size':3}).json()['id']
    with factory() as db:
        actor=db.get(User,1)
        actor.is_active=False
        db.get(UploadSession,upload_id).expires_at=utcnow()-timedelta(seconds=1)
        db.commit()
        with pytest.raises(storage.StorageError):
            with storage.owner_guard(db,1):
                raise AssertionError('disabled actor must not gain file access')
        with storage.owner_lock(db,1):
            assert storage.expire_uploads(db,1)==1
            db.commit()
        assert db.get(UploadSession,upload_id).state=='expired'
    assert not storage.upload_path(upload_id).exists()


def test_failed_exclusive_temp_creation_does_not_delete_existing_bytes(env,monkeypatch):
    client,factory=env
    existing=storage.storage_root()/'unrelated-temp'
    existing.parent.mkdir(parents=True,exist_ok=True)
    existing.write_bytes(b'preserve collision')
    monkeypatch.setattr(storage,'upload_path',lambda upload_id:existing)
    assert client.post('/api/uploads',json={'name':'no-overwrite','size':3}).status_code==503
    assert existing.read_bytes()==b'preserve collision'
    with factory() as db:
        assert db.query(UploadSession).count()==0


def test_personal_abort_rejects_legacy_unbound_team_session(env):
    client,factory=env
    group=team(client)
    with factory() as db:
        root=db.get(Team,group['id']).root_id
        row=UploadSession(owner_id=1,parent_id=root,name='legacy-unbound',size=7,
                          expires_at=utcnow()+timedelta(hours=1))
        db.add(row);db.commit();upload_id=row.id
    path=storage.upload_path(upload_id)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(b'pending')
    assert client.delete(f'/api/uploads/{upload_id}').status_code==404
    assert path.read_bytes()==b'pending'
    with factory() as db:
        assert db.get(UploadSession,upload_id).state=='pending'
