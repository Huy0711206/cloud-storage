"""Real temporary filesystem + isolated SQLite; no Nextcloud, SMTP or payment calls."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import hashlib
import threading

import pytest
from fastapi import Depends, FastAPI, Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.models import Plan, User, utcnow
from app.shared.http import current_user
from app.features.storage.native_models import FileNode, StorageGarbage, UploadSession
from app.features.storage import native_service as service
from app.features.storage.routes import router


@pytest.fixture
def env(tmp_path,monkeypatch):
    monkeypatch.setenv("STORAGE_ROOT",str(tmp_path/"storage"))
    monkeypatch.setattr(settings,"base_url","http://testserver")
    engine=create_engine("sqlite:///"+str(tmp_path/"isolated.db"),connect_args={"check_same_thread":False})
    @event.listens_for(engine,"connect")
    def foreign_keys(connection,_):connection.execute("PRAGMA foreign_keys=ON")
    factory=sessionmaker(engine,expire_on_commit=False,autoflush=False)
    Base.metadata.create_all(engine)
    with factory() as db:
        plan=Plan(code="isolated",name="Isolated",quota_gb=1,price_vnd=0,sort=0)
        db.add(plan);db.flush()
        for index in (1,2,3):
            db.add(User(id=index,email=f"native-{index}@gmail.com",full_name="Native test",password_hash="not-used-in-test",role="user",is_active=True,is_verified=index!=3,plan_id=plan.id))
        db.commit()
    app=FastAPI();app.include_router(router)
    def test_db():
        with factory() as db:yield db
    def test_current(request:Request,db=Depends(get_db)):
        uid=request.headers.get("x-test-user")
        return db.get(User,int(uid)) if uid else None
    app.dependency_overrides[get_db]=test_db
    app.dependency_overrides[current_user]=test_current
    with TestClient(app,headers={"x-test-user":"1"}) as client:yield client,factory
    engine.dispose()


def folder(client,name="Documents",parent=None):
    r=client.post("/api/files/folders",json={"name":name,"parent_id":parent})
    assert r.status_code==201,r.text
    return r.json()["id"]


def upload(client,name="hello.txt",data=b"native cloudbox",parent=None):
    r=client.post("/api/uploads",json={"name":name,"parent_id":parent,"size":len(data)})
    assert r.status_code==201,r.text
    uid=r.json()["id"]
    r=client.put("/api/uploads/"+uid,content=data,headers={"Upload-Offset":"0"})
    assert r.status_code==200,r.text
    r=client.post("/api/uploads/"+uid+"/complete")
    assert r.status_code==200,r.text
    return r.json(),uid


def test_upload_download_same_bytes_and_usage(env):
    client,_=env
    data=b"\x00bytes\xff"*23
    item,uid=upload(client,data=data)
    assert item["sha256"]==hashlib.sha256(data).hexdigest()
    response=client.get(f'/api/files/{item["id"]}/download')
    assert response.content==data
    assert response.headers["x-content-type-options"]=="nosniff"
    assert "attachment" in response.headers["content-disposition"]
    assert client.post("/api/uploads/"+uid+"/complete").json()["id"]==item["id"]
    assert client.get("/api/storage/usage").json()["used"]==len(data)


def test_owner_authorization_on_every_resource(env):
    client,_=env
    parent=folder(client)
    item,uid=upload(client,parent=parent)
    share=client.post(f'/api/files/{item["id"]}/shares').json()
    client.headers["x-test-user"]="2"
    for path in [f'/api/files/{item["id"]}',f'/api/files/{item["id"]}/download',f'/api/files/{item["id"]}/shares',f'/api/files?parent={parent}']:
        assert client.get(path).status_code==404
    assert client.patch(f'/api/files/{item["id"]}',json={"name":"taken"}).status_code==404
    assert client.post(f'/api/files/{item["id"]}/trash').status_code==404
    assert client.post(f'/api/files/{item["id"]}/restore').status_code==404
    assert client.delete('/api/uploads/'+uid).status_code==404
    assert client.delete('/api/shares/'+share["id"]).status_code==404
    assert client.post('/api/files/folders',json={"name":"no","parent_id":parent}).status_code==404


def test_path_names_and_cycle_rejected(env):
    client,_=env
    for name in ["..","../escape","a/b","a\\b","bad\x00name"," ","control\nname"]:
        assert client.post('/api/files/folders',json={"name":name}).status_code in (400,422)
    first=folder(client,"first")
    second=folder(client,"second",first)
    assert client.patch('/api/files/'+first,json={"parent_id":second}).status_code==409
    assert client.patch('/api/files/'+first,json={"parent_id":first}).status_code==409
    assert client.post('/api/files/folders',json={"name":"first"}).status_code==409
    assert client.get('/api/files?parent='+second).json()["ancestors"]==[{"id":first,"name":"first"},{"id":second,"name":"second"}]


def test_move_rename_search_and_literal_wildcards(env):
    client,_=env
    first=folder(client,"first");second=folder(client,"second")
    item,_=upload(client,name="100%_notes.txt",parent=first)
    r=client.patch('/api/files/'+item['id'],json={"parent_id":second,"name":"100%_renamed.txt"})
    assert r.status_code==200
    assert not client.get('/api/files?parent='+first).json()["items"]
    assert client.get('/api/files',params={"q":"%_renamed"}).json()["items"][0]["id"]==item["id"]
    assert not client.get('/api/files',params={"q":"%_missing"}).json()["items"]


def test_trash_restore_conflict_and_quota_retained(env):
    client,_=env
    parent=folder(client)
    item,_=upload(client,data=b"12345",parent=parent)
    assert client.post('/api/files/'+parent+'/trash').status_code==200
    assert client.get('/api/storage/usage').json()["used"]==5
    assert client.get('/api/files/'+item['id']+'/download').status_code==404
    trash=client.get('/api/files?trash=true').json()["items"]
    assert len(trash)==1 and trash[0]["id"]==parent
    assert client.post('/api/files/'+item['id']+'/restore').status_code==409
    replacement=folder(client)
    assert client.post('/api/files/'+parent+'/restore').status_code==409
    assert client.patch('/api/files/'+replacement,json={"name":"replacement"}).status_code==200
    assert client.post('/api/files/'+parent+'/restore').status_code==200
    assert client.get('/api/files/'+item['id']+'/download').content==b"12345"


def test_read_only_share_subtree_and_revocation(env):
    client,_=env
    parent=folder(client,'<script>alert("x")</script>'.replace('/','-'))
    inside,_=upload(client,parent=parent)
    outside,_=upload(client,name="private.txt")
    share=client.post('/api/files/'+parent+'/shares').json()
    assert share["permission"]=="read"
    token=share["token"]
    page=client.get('/s/'+token)
    assert page.status_code==200 and '&lt;script&gt;' in page.text and '<script>' not in page.text
    assert client.get('/s/'+token+'/download/'+inside['id']).content==b"native cloudbox"
    assert client.get('/s/'+token+'/download/'+outside['id']).status_code==404
    assert client.get('/s/'+token,params={"folder":outside['id']}).status_code==404
    assert client.get('/api/shares').json()["items"][0]["file_id"]==parent
    assert client.post('/api/files/'+parent+'/trash').status_code==200
    assert client.get('/s/'+token).status_code==404
    assert client.post('/api/files/'+parent+'/restore').status_code==200
    assert client.delete('/api/shares/'+share['id']).status_code==200
    assert client.get('/s/'+token).status_code==404


def test_chunk_offsets_size_and_abort_release_reservation(env):
    client,_=env
    r=client.post('/api/uploads',json={"name":"data.bin","size":8})
    uid=r.json()["id"]
    assert client.get('/api/storage/usage').json()["reserved"]==8
    assert client.put('/api/uploads/'+uid,content=b"1234",headers={"Upload-Offset":"0"}).json()["received"]==4
    assert client.put('/api/uploads/'+uid,content=b"1234",headers={"Upload-Offset":"0"}).status_code==409
    assert client.put('/api/uploads/'+uid,content=b"12345",headers={"Upload-Offset":"4"}).status_code==400
    assert client.post('/api/uploads/'+uid+'/complete').status_code==409
    assert client.delete('/api/uploads/'+uid).status_code==200
    assert client.get('/api/storage/usage').json()["reserved"]==0
    assert not service.upload_path(uid).exists()


def test_reservations_prevent_parallel_quota_overallocation(env):
    _,factory=env
    barrier=threading.Barrier(2)
    def reserve(index):
        with factory() as db:
            u=db.get(User,1);barrier.wait()
            try:service.start_upload(db,u,f"large{index}.bin",None,700*1024**2);return 201
            except service.StorageError as exc:return exc.status
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(reserve,[1,2]))==[201,413]


def test_expired_upload_cannot_complete_and_can_be_cleaned(env):
    client,factory=env
    uid=client.post('/api/uploads',json={"name":"expired","size":0}).json()["id"]
    with factory() as db:
        db.get(UploadSession,uid).expires_at=utcnow()-timedelta(seconds=1);db.commit()
    assert client.post('/api/uploads/'+uid+'/complete').status_code==409
    assert client.get('/api/storage/usage').json()["reserved"]==0
    with factory() as db:
        assert service.expire_uploads(db,1)==1;db.commit()
    assert not service.upload_path(uid).exists()


def test_empty_file_and_crash_recovery_between_rename_and_commit(env):
    client,_=env
    uid=client.post('/api/uploads',json={"name":"empty.txt","size":0}).json()["id"]
    source=service.upload_path(uid);dest=service.blob_path(uid)
    dest.parent.mkdir(parents=True,exist_ok=True);source.replace(dest)
    r=client.post('/api/uploads/'+uid+'/complete')
    assert r.status_code==200,r.text
    assert client.get('/api/files/'+r.json()['id']+'/download').content==b""


def test_authentication_and_cross_origin_mutations(env):
    client,_=env
    assert client.post('/api/files/folders',json={"name":"blocked"},headers={"Origin":"https://evil.invalid"}).status_code==403
    assert client.post('/api/files/folders',json={"name":"blocked"},headers={"Sec-Fetch-Site":"cross-site"}).status_code==403
    client.headers["x-test-user"]="3"
    assert client.get('/api/files').status_code==403
    client.headers.pop("x-test-user")
    r=client.get('/api/files')
    assert r.status_code==401 and r.json().get('detail')


def test_purge_requires_trashed_root_confirmation_and_frees_space(env):
    client,factory=env
    parent=folder(client)
    item,_=upload(client,parent=parent,data=b"contents")
    pending=client.post('/api/uploads',json={"name":"pending","parent_id":parent,"size":5}).json()['id']
    share=client.post('/api/files/'+parent+'/shares').json()
    with factory() as db:key=db.get(FileNode,item['id']).blob_key
    assert client.request('DELETE','/api/files/'+parent,json={"confirm_id":parent}).status_code==409
    client.post('/api/files/'+parent+'/trash')
    assert client.request('DELETE','/api/files/'+parent,json={"confirm_id":"wrong"}).status_code==400
    assert client.request('DELETE','/api/files/'+item['id'],json={"confirm_id":item['id']}).status_code==409
    response=client.request('DELETE','/api/files/'+parent,json={"confirm_id":parent})
    assert response.status_code==200,response.text
    assert response.json()['purged_count']==2
    assert response.json()['usage']['used']==0 and response.json()['usage']['reserved']==0
    assert not service.blob_path(key).exists() and not service.upload_path(pending).exists()
    assert client.get('/s/'+share['token']).status_code==404
    assert client.get('/api/files?trash=true').json()['items']==[]


def test_purge_queues_failed_physical_cleanup_and_retry(env,monkeypatch):
    client,factory=env
    item,_=upload(client,data=b"keep until cleanup")
    client.post('/api/files/'+item['id']+'/trash')
    collector=service.collect_garbage
    monkeypatch.setattr(service,'collect_garbage',lambda *args:0)
    response=client.request('DELETE','/api/files/'+item['id'],json={"confirm_id":item['id']})
    assert response.status_code==200 and response.json()['cleanup_pending'] is True
    with factory() as db:
        assert db.get(FileNode,item['id']) is None
        assert db.query(StorageGarbage).count()==1
        assert collector(db)==1
        assert db.query(StorageGarbage).count()==0
