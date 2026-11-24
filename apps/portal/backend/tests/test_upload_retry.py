"""Personal session progress and commit acknowledgements in isolated storage."""
from datetime import timedelta

from app.core.models import utcnow
from app.features.storage.native_models import UploadSession
from test_collaboration_features import env, request, team


def test_progress_supports_resending_only_unconfirmed_bytes_and_completion(env):
    client, _ = env
    data = b"partone-parttwo"
    created = client.post("/api/uploads", json={"name": "retry.txt", "size": len(data)})
    assert created.status_code == 201
    session = "/api/uploads/" + created.json()["id"]

    before = client.get(session)
    assert before.json() == {"received": 0, "size": len(data)}
    assert "no-store" in before.headers["cache-control"]
    # Model missing client acknowledgements by checking server state after a successful write.
    assert client.put(session, content=data[:7], headers={"Upload-Offset": "0"}).status_code == 200
    acknowledged = client.get(session).json()["received"]
    assert acknowledged == 7
    assert client.put(session, content=data[acknowledged:], headers={"Upload-Offset": str(acknowledged)}).status_code == 200
    original = client.post(session + "/complete")
    repeated = client.post(session + "/complete")
    assert original.status_code == repeated.status_code == 200
    file_id = original.json()["id"]
    assert repeated.json()["id"] == file_id
    assert client.get(f"/api/files/{file_id}/download").content == data
    listing = client.get("/api/files").json()
    assert [item["id"] for item in listing["items"]] == [file_id]
    assert listing["usage"]["used"] == len(data) and listing["usage"]["reserved"] == 0


def test_progress_requires_personal_session_owner(env):
    client, _ = env
    personal = client.post("/api/uploads", json={"name": "personal.txt", "size": 4}).json()["id"]
    group = team(client)
    group_session = client.post(f'/api/teams/{group["id"]}/uploads', json={"name": "team.txt", "size": 4})
    assert group_session.status_code == 201
    _, token = request(client)
    inbox = client.post(f"/api/requests/{token}/uploads", json={"name": "inbox.txt", "size": 4})
    assert inbox.status_code == 201
    for foreign in (group_session.json()["id"], inbox.json()["id"]):
        assert client.get("/api/uploads/" + foreign).status_code == 404
    assert client.get("/api/uploads/" + personal, headers={"x-user": "2"}).status_code == 404
    client.headers.pop("x-user")
    assert client.get("/api/uploads/" + personal).status_code == 401


def test_progress_distinguishes_closed_and_expired_sessions(env):
    client, db_factory = env
    closed = client.post("/api/uploads", json={"name": "canceled.txt", "size": 1}).json()["id"]
    expired = client.post("/api/uploads", json={"name": "expired.txt", "size": 2}).json()["id"]
    assert client.delete("/api/uploads/" + closed).status_code == 200
    with db_factory() as db:
        db.get(UploadSession, expired).expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
    for session in (closed, expired):
        assert client.get("/api/uploads/" + session).status_code == 409
    assert client.get("/api/storage/usage").json()["reserved"] == 0
