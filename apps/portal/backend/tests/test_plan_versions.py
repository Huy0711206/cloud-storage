"""Revision, quota and authorization proofs using disposable files/SQLite only."""
from datetime import timedelta

import pytest

from app.core.models import User, Plan, utcnow
from app.features.storage import native_service as s
from app.features.storage.migration_models import FileVersion
from app.features.storage.native_models import FileNode
from app.features.storage.version_models import VersionPolicy
from app.features.storage.version_routes import router
from app.features.storage.version_service import restore_version
from test_native_storage import env, upload


@pytest.fixture
def version_env(env):
    client, factory = env
    client.app.include_router(router)
    with factory() as db:
        plan = db.query(Plan).one()
        plan.code, plan.name, plan.price_vnd = "basic", "Cơ bản", 39000
        db.commit()
    return client, factory


def replacement(factory, node, data):
    with factory() as db:
        user = db.get(User, 1)
        session = s.start_upload(db, user, node["name"], node["parent_id"], len(data), node["id"])
        s.append_chunk(db, user, session["id"], data, 0)
        return session["id"]


def complete(factory, upload_id):
    with factory() as db:
        return s.finish_upload(db, db.get(User, 1), upload_id)


def test_explicit_replacement_preserves_current_as_history_and_quota(version_env):
    client, factory = version_env
    node, _ = upload(client, data=b"old bytes")
    # Duplicate ordinary uploads never overwrite implicitly.
    assert client.post("/api/uploads", json={"name":node["name"],"size":3}).status_code == 409
    session = replacement(factory, node, b"new bytes!")
    result = complete(factory, session)
    assert result["id"] == node["id"]
    assert complete(factory, session)["id"] == node["id"]  # retry is idempotent
    assert client.get(f'/api/files/{node["id"]}/download').content == b"new bytes!"
    history = client.get(f'/api/files/{node["id"]}/versions').json()
    version = history["items"][0]
    assert len(history["items"]) == 1
    assert version["source"] == "native" and version["available"] and version["restorable"]
    assert version["expires_at"] is not None and history["retention_days"] == 30
    assert client.get(f'/api/files/{node["id"]}/versions/{version["id"]}/download').content == b"old bytes"
    assert client.get("/api/storage/usage").json()["used"] == len(b"old bytes") + len(b"new bytes!")


def test_two_replacements_cannot_silently_overwrite_each_other(version_env):
    client, factory = version_env
    node, _ = upload(client, data=b"initial")
    first = replacement(factory, node, b"first")
    second = replacement(factory, node, b"second")
    complete(factory, first)
    with pytest.raises(s.StorageError) as exc:
        complete(factory, second)
    assert exc.value.status == 409
    assert client.get(f'/api/files/{node["id"]}/download').content == b"first"
    assert len(client.get(f'/api/files/{node["id"]}/versions').json()["items"]) == 1
    with factory() as db:
        s.abort_upload(db, db.get(User, 1), second)
    assert client.get("/api/storage/usage").json()["reserved"] == 0


def test_restore_archives_current_and_keeps_selected_history(version_env):
    client, factory = version_env
    node, _ = upload(client, data=b"original")
    complete(factory, replacement(factory, node, b"edited"))
    version = client.get(f'/api/files/{node["id"]}/versions').json()["items"][0]
    response = client.post(f'/api/files/{node["id"]}/versions/{version["id"]}/restore')
    assert response.status_code == 200, response.text
    assert client.get(f'/api/files/{node["id"]}/download').content == b"original"
    versions = client.get(f'/api/files/{node["id"]}/versions').json()["items"]
    assert len(versions) == 2
    contents = [client.get(f'/api/files/{node["id"]}/versions/{v["id"]}/download').content for v in versions]
    assert set(contents) == {b"original", b"edited"}
    assert response.json()["usage"]["used"] == len(b"original") * 2 + len(b"edited")


def test_restore_and_replace_enforce_quota_without_losing_current(version_env):
    client, factory = version_env
    node, _ = upload(client, data=b"original")
    complete(factory, replacement(factory, node, b"edited"))
    version = client.get(f'/api/files/{node["id"]}/versions').json()["items"][0]
    with factory() as db:
        db.query(Plan).one().quota_gb = 0
        db.commit()
    assert client.post(f'/api/files/{node["id"]}/versions/{version["id"]}/restore').status_code == 413
    with pytest.raises(s.StorageError) as exc:
        replacement(factory, node, b"blocked")
    assert exc.value.status == 413
    assert client.get(f'/api/files/{node["id"]}/download').content == b"edited"


def test_expired_window_preserves_bytes_and_imported_history(version_env):
    client, factory = version_env
    node, _ = upload(client, data=b"original")
    complete(factory, replacement(factory, node, b"edited"))
    with factory() as db:
        version = db.query(FileVersion).one()
        version_id, key = version.id, version.blob_key
        db.get(VersionPolicy, version.id).expires_at = utcnow() - timedelta(seconds=1)
        db.add(FileVersion(owner_id=1, node_id=node["id"], source_key="legacy:test", name=node["name"],
                           size=version.size, blob_key=key, sha256=version.sha256,
                           created_at=utcnow() - timedelta(days=500)))
        db.commit()
    assert client.get(f'/api/files/{node["id"]}/versions/{version_id}/download').status_code == 410
    versions = client.get(f'/api/files/{node["id"]}/versions').json()["items"]
    imported = next(v for v in versions if v["source"] == "imported")
    assert imported["available"] and imported["expires_at"] is None
    assert client.get(f'/api/files/{node["id"]}/versions/{imported["id"]}/download').content == b"original"
    assert s.blob_path(key).is_file()
    with factory() as db:
        assert db.query(FileVersion).count() == 2


def test_downgrade_does_not_shorten_saved_window_and_blocks_new_replacement(version_env):
    client, factory = version_env
    node, _ = upload(client, data=b"original")
    complete(factory, replacement(factory, node, b"edited"))
    version = client.get(f'/api/files/{node["id"]}/versions').json()["items"][0]
    with factory() as db:
        plan = db.query(Plan).one()
        plan.code, plan.price_vnd = "free", 0
        db.commit()
    assert client.get(f'/api/files/{node["id"]}/versions/{version["id"]}/download').content == b"original"
    assert client.post(f'/api/files/{node["id"]}/versions/{version["id"]}/restore').status_code == 403
    with pytest.raises(s.StorageError) as exc:
        replacement(factory, node, b"blocked")
    assert exc.value.status == 403


def test_versions_authorization_and_origin_guard(version_env):
    client, factory = version_env
    node, _ = upload(client, data=b"original")
    complete(factory, replacement(factory, node, b"edited"))
    version = client.get(f'/api/files/{node["id"]}/versions').json()["items"][0]
    endpoint = f'/api/files/{node["id"]}/versions/{version["id"]}'
    assert client.post(endpoint+"/restore",headers={"Origin":"https://evil.example"}).status_code == 403
    client.headers["x-test-user"] = "2"
    assert client.get(f'/api/files/{node["id"]}/versions').status_code == 404
    assert client.get(endpoint+"/download").status_code == 404
    assert client.post(endpoint+"/restore").status_code == 404
    with factory() as db:
        with pytest.raises(s.StorageError) as exc:
            s.start_upload(db, db.get(User,2), node["name"], None, 0, node["id"])
        assert exc.value.status == 404


@pytest.mark.parametrize("code,days", [("basic",30),("standard",90),("premium",180)])
def test_snapshot_retention_follows_plan_at_creation(version_env,code,days):
    client,factory=version_env
    with factory() as db:
        plan=db.query(Plan).one()
        plan.code=code
        db.commit()
    node,_=upload(client,data=b"original")
    complete(factory,replacement(factory,node,b"edited"))
    with factory() as db:
        version=db.query(FileVersion).one()
        policy=db.get(VersionPolicy,version.id)
        assert policy.plan_code==code
        assert abs((policy.expires_at-version.created_at).total_seconds()-days*86400)<1
