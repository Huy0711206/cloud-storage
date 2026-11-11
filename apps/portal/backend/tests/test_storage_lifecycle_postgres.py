"""Opt-in scope/row-lock checks, restricted to the disposable cloudbox_qa DB."""
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from datetime import timedelta
from threading import Barrier, Event

import pytest
from sqlalchemy import text

from app.core.models import Plan, User, utcnow
from app.features.storage import native_service as storage
from app.features.storage import request_service as requests
from app.features.storage import team_service as teams
from app.features.storage.collaboration_models import RequestUpload, TeamUpload
from app.features.storage.native_models import FileNode, UploadSession
from test_native_postgres import pg


def premium_owner_and_member(sessions, owner_id):
    with sessions() as db:
        plan = Plan(code="premium", name="Premium", quota_gb=2048, price_vnd=199000)
        db.add(plan)
        db.flush()
        owner = db.get(User, owner_id)
        owner.plan_id = plan.id
        owner.plan_expires_at = utcnow() + timedelta(days=30)
        member = User(email="lifecycle-member@gmail.com", full_name="Disposable member",
                      password_hash="unused", is_active=True, is_verified=True, plan_id=plan.id,
                      plan_expires_at=utcnow() + timedelta(days=30))
        db.add(member)
        db.commit()
        member_id = member.id
        group = teams.create_team(db, owner, "Disposable team")
        invitation = teams.invite(db, owner, group["id"], member.email, "editor")
        teams.accept_invitation(db, member, invitation["id"])
    return group, member_id


@pytest.mark.parametrize("attribute", ["is_active", "is_verified"])
def test_upload_completion_waits_for_concurrent_actor_revocation(pg, monkeypatch, attribute):
    sessions, owner_id = pg
    monkeypatch.setenv("STORAGE_POOL_LIMIT_BYTES", "0")
    group, member_id = premium_owner_and_member(sessions, owner_id)
    with sessions() as db:
        actor = db.get(User, member_id)
        upload = teams.team_upload(db, actor, group["id"], "pending.bin", None, 3)
        teams.team_upload_action(db, actor, group["id"], upload["id"], "chunk", b"abc", 0)

    started = Event()

    def finish():
        with sessions() as db:
            db.execute(text("SET LOCAL statement_timeout = '5s'"))
            actor = db.get(User, member_id)
            assert getattr(actor, attribute)
            started.set()
            try:
                teams.team_upload_action(db, actor, group["id"], upload["id"], "complete")
                return 200
            except storage.StorageError as exc:
                return exc.status

    with sessions() as revocation:
        actor = revocation.query(User).filter_by(id=member_id).with_for_update().one()
        setattr(actor, attribute, False)
        revocation.flush()
        pool = ThreadPoolExecutor(1)
        try:
            pending = pool.submit(finish)
            assert started.wait(5)
            # An uncommitted actor change must hold completion at the actor row lock.
            with pytest.raises(TimeoutError):
                pending.result(timeout=0.25)
            revocation.commit()
            assert pending.result(timeout=5) == 403
        finally:
            revocation.rollback()
            pool.shutdown(wait=True)
    with sessions() as db:
        assert db.get(UploadSession, upload["id"]).state == "pending"
        assert db.query(FileNode).filter_by(is_folder=False).count() == 0
    assert storage.upload_path(upload["id"]).read_bytes() == b"abc"


def test_team_and_request_reservations_share_one_pg_pool_lock(pg, monkeypatch):
    sessions, owner_id = pg
    group, receiver_id = premium_owner_and_member(sessions, owner_id)
    with sessions() as db:
        receiver = db.get(User, receiver_id)
        parent = storage.create_folder(db, receiver, "Inbox", None)
        inbox = requests.create_request(db, receiver, "Receive", parent["id"], 7, 64, 128)
        token = inbox["url"].split("/r/")[1]
    monkeypatch.setenv("STORAGE_POOL_LIMIT_BYTES", "5")
    barrier = Barrier(2)

    def reserve(scope):
        with sessions() as db:
            db.execute(text("SET LOCAL statement_timeout = '5s'"))
            barrier.wait(timeout=5)
            try:
                if scope == "team":
                    result = teams.team_upload(db, db.get(User, owner_id), group["id"], "team.bin", None, 3)
                else:
                    result = requests.start_public_upload(db, token, "request.bin", 3)
                return 201, result["id"]
            except storage.StorageError as exc:
                return exc.status, None

    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(reserve, ("team", "request")))
    assert sorted(status for status, _ in results) == [201, 507]
    accepted_id = next(upload_id for status, upload_id in results if status == 201)
    with sessions() as db:
        assert db.query(UploadSession).count() == 1
        assert db.get(UploadSession, accepted_id).state == "pending"
        assert db.query(TeamUpload).count() + db.query(RequestUpload).count() == 1
    assert [path.name for path in (storage.storage_root() / "uploads").iterdir()] == [accepted_id]
