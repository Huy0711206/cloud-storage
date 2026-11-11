"""Real signed sessions + temporary SQLite; no SMTP/payment/network dependencies."""
from datetime import timedelta
import re

import pytest
from fastapi import Depends, FastAPI, Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.models import Plan, User, utcnow
from app.shared.http import current_user
from app.features.storage.native_models import FileShare
from app.features.storage.share_models import ShareProtection, ShareStatistics
from app.features.storage.routes import router
from test_native_storage import upload, folder


@pytest.fixture
def shares_env(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_ROOT",str(tmp_path/"storage"))
    monkeypatch.setattr(settings,"base_url","http://testserver")
    engine=create_engine("sqlite:///"+str(tmp_path/"shares.db"),connect_args={"check_same_thread":False})
    @event.listens_for(engine,"connect")
    def foreign_keys(connection,_):
        connection.execute("PRAGMA foreign_keys=ON")
    factory=sessionmaker(engine,expire_on_commit=False,autoflush=False)
    Base.metadata.create_all(engine)
    with factory() as db:
        plan=Plan(code="premium",name="Cao cấp",quota_gb=2048,price_vnd=199000)
        db.add(plan);db.flush()
        for uid in (1,2):
            db.add(User(id=uid,email=f"shares-{uid}@gmail.com",full_name="Share QA",password_hash="unused",is_active=True,is_verified=True,plan_id=plan.id))
        db.commit()
    app=FastAPI()
    app.add_middleware(SessionMiddleware,secret_key="isolated-share-session-key",same_site="lax",https_only=False)
    app.include_router(router)
    def test_db():
        with factory() as db:yield db
    def test_user(request:Request,db=Depends(get_db)):
        uid=request.headers.get("x-test-user")
        return db.get(User,int(uid)) if uid else None
    app.dependency_overrides[get_db]=test_db
    app.dependency_overrides[current_user]=test_user
    with TestClient(app,headers={"x-test-user":"1"}) as client:
        yield client,factory
    engine.dispose()


def create(client,node,password=None,expires=None):
    result=client.post(f'/api/files/{node["id"]}/shares',json={"password":password,"expires_at":expires})
    assert result.status_code==201,result.text
    return result.json()


def unlock(client,share,password):
    page=client.get("/s/"+share["token"])
    csrf=re.search(r'name="csrf_token" value="([^"]+)"',page.text)
    return client.post("/s/"+share["token"]+"/unlock",data={"password":password,"csrf_token":csrf.group(1) if csrf else ""},follow_redirects=False)


def test_protected_share_challenges_and_direct_download_cannot_bypass(shares_env):
    client,factory=shares_env
    node,_=upload(client,name="private-name.txt",data=b"secret content")
    share=create(client,node,password="correct-link-password")
    client.headers.pop("x-test-user")
    url="/s/"+share["token"]
    page=client.get(url)
    assert page.status_code==200 and "Mật khẩu liên kết" in page.text
    assert node["name"] not in page.text
    assert client.get(url+"/download/"+node["id"]).status_code==401
    assert unlock(client,share,"incorrect-password").status_code==401
    assert unlock(client,share,"correct-link-password").status_code==303
    assert client.get(url+"/download/"+node["id"]).content==b"secret content"
    # Neither password nor the stored password hash appears in the signed cookie.
    with factory() as db:
        protection=db.get(ShareProtection,share["id"])
        assert protection.password_hash!="correct-link-password"
        assert "correct-link-password" not in client.cookies.get("session","")
    client.cookies.clear()
    assert client.get(url+"/download/"+node["id"]).status_code==401


def test_unlock_grant_is_scoped_to_share_and_revoke_remains_authoritative(shares_env):
    client,_=shares_env
    node,_=upload(client,data=b"bytes")
    first=create(client,node,password="shared-password")
    second=create(client,node,password="shared-password")
    assert unlock(client,first,"shared-password").status_code==303
    assert client.get(f'/s/{second["token"]}/download/{node["id"]}').status_code==401
    assert client.delete("/api/shares/"+first["id"]).status_code==200
    assert client.get(f'/s/{first["token"]}/download/{node["id"]}').status_code==404


def test_expiry_is_checked_on_page_and_download_after_unlock(shares_env):
    client,factory=shares_env
    node,_=upload(client,data=b"bytes")
    expiry=(utcnow()+timedelta(hours=2)).isoformat()+"Z"
    share=create(client,node,password="expiry-password",expires=expiry)
    assert unlock(client,share,"expiry-password").status_code==303
    with factory() as db:
        db.get(FileShare,share["id"]).expires_at=utcnow()-timedelta(seconds=1)
        db.commit()
    assert client.get("/s/"+share["token"]).status_code==404
    assert client.get(f'/s/{share["token"]}/download/{node["id"]}').status_code==404


def test_password_attempts_are_limited_and_persist_through_failures(shares_env):
    client,_=shares_env
    node,_=upload(client,data=b"bytes")
    share=create(client,node,password="correct-password")
    for _ in range(20):
        assert unlock(client,share,"wrong-password").status_code==401
    assert unlock(client,share,"correct-password").status_code==429
    assert client.get(f'/s/{share["token"]}/download/{node["id"]}').status_code==401


def test_downgrade_keeps_existing_protections_and_denies_new_controls(shares_env):
    client,factory=shares_env
    node,_=upload(client,data=b"bytes")
    share=create(client,node,password="saved-password",expires=(utcnow()+timedelta(days=1)).isoformat()+"Z")
    with factory() as db:
        plan=db.query(Plan).one()
        plan.code,plan.price_vnd="free",0
        db.commit()
    assert client.get(f'/s/{share["token"]}/download/{node["id"]}').status_code==401
    assert unlock(client,share,"saved-password").status_code==303
    assert client.get(f'/s/{share["token"]}/download/{node["id"]}').content==b"bytes"
    assert client.post(f'/api/files/{node["id"]}/shares',json={"password":"new-password"}).status_code==403
    assert client.post(f'/api/files/{node["id"]}/shares',json={"expires_at":(utcnow()+timedelta(days=1)).isoformat()+"Z"}).status_code==403
    # Ordinary links remain available on free.
    assert client.post(f'/api/files/{node["id"]}/shares').status_code==201


def test_statistics_are_aggregate_and_owner_only(shares_env):
    client,factory=shares_env
    node,_=upload(client,data=b"bytes")
    share=create(client,node)
    for _ in range(2):assert client.get("/s/"+share["token"]).status_code==200
    assert client.get(f'/s/{share["token"]}/download/{node["id"]}').status_code==200
    items=client.get(f'/api/files/{node["id"]}/shares').json()["items"]
    assert items[0]["views"]==2 and items[0]["downloads"]==1 and items[0]["stats_since"]
    assert "viewers" not in items[0] and "ip" not in items[0]
    client.headers["x-test-user"]="2"
    assert client.get(f'/api/files/{node["id"]}/shares').status_code==404
    assert client.delete("/api/shares/"+share["id"]).status_code==404
    assert client.get("/api/shares").json()["items"]==[]


def test_share_controls_validate_timezone_and_password_length(shares_env):
    client,_=shares_env
    node,_=upload(client,data=b"bytes")
    for body in [{"password":"short"},{"expires_at":"2028-01-01T00:00:00"},{"expires_at":"invalid"},{"expires_at":"2000-01-01T00:00:00Z"}]:
        assert client.post(f'/api/files/{node["id"]}/shares',json=body).status_code==400


def test_public_link_cannot_escape_shared_folder(shares_env):
    client,_=shares_env
    shared_folder=folder(client,"shared")
    inside,_=upload(client,name="inside.txt",parent=shared_folder)
    outside,_=upload(client,name="outside.txt",data=b"outside")
    share=create(client,{"id":shared_folder},password="folder-password")
    assert unlock(client,share,"folder-password").status_code==303
    assert client.get(f'/s/{share["token"]}/download/{inside["id"]}').status_code==200
    assert client.get(f'/s/{share["token"]}/download/{outside["id"]}').status_code==404


def test_permanent_purge_cascades_new_share_metadata(shares_env):
    client,factory=shares_env
    node,_=upload(client,data=b'purge example')
    share=create(client,node,password='safe-test-pass')
    assert client.post('/s/'+share['token']+'/unlock',data={'password':'safe-test-pass'}).status_code==200
    client.get('/s/'+share['token'])
    assert client.post('/api/files/'+node['id']+'/trash').status_code==200
    response=client.request('DELETE','/api/files/'+node['id'],json={'confirm_id':node['id']})
    assert response.status_code==200,response.text
    with factory() as db:
        assert db.query(ShareProtection).count()==0 and db.query(ShareStatistics).count()==0
