"""Isolated filesystem/database checks for team boundaries and upload-only capabilities."""
from datetime import timedelta
import pytest
from fastapi import FastAPI,Depends,Request
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import create_engine,event
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.core.database import Base,get_db
from app.core.models import User,Plan,utcnow
from app.shared.http import current_user
from app.features.storage.routes import router as personal
from app.features.storage.collaboration_routes import router
from app.features.storage.team_version_routes import router as version_router
from app.features.storage.collaboration_models import FileRequest,TeamMember
from app.features.storage.native_models import FileNode,UploadSession

@pytest.fixture
def env(tmp_path,monkeypatch):
    monkeypatch.setenv('STORAGE_ROOT',str(tmp_path/'storage'));monkeypatch.setattr(settings,'base_url','http://testserver')
    engine=create_engine('sqlite:///'+str(tmp_path/'test.db'),connect_args={'check_same_thread':False})
    @event.listens_for(engine,'connect')
    def fk(conn,_):conn.execute('PRAGMA foreign_keys=ON')
    factory=sessionmaker(engine,expire_on_commit=False,autoflush=False);Base.metadata.create_all(engine)
    with factory() as db:
        for code,size,price in [('free',5,0),('basic',100,39000),('standard',500,89000),('premium',2048,199000)]:db.add(Plan(code=code,name=code,quota_gb=size,price_vnd=price))
        db.flush();plans={p.code:p.id for p in db.query(Plan)}
        for i in range(1,9):db.add(User(id=i,email=f'member{i}@gmail.com',full_name=f'User {i}',password_hash='unused',is_verified=True,is_active=True,plan_id=plans['premium'] if i in (1,8) else plans['free'],plan_expires_at=utcnow()+timedelta(days=30) if i in (1,8) else None))
        db.commit()
    app=FastAPI();app.add_middleware(SessionMiddleware,secret_key='isolated-secret');app.include_router(personal);app.include_router(router);app.include_router(version_router)
    def test_db():
        with factory() as db:yield db
    def test_user(request:Request,db=Depends(get_db)):
        return db.get(User,int(request.headers['x-user'])) if request.headers.get('x-user') else None
    app.dependency_overrides[get_db]=test_db;app.dependency_overrides[current_user]=test_user
    with TestClient(app,headers={'x-user':'1'}) as client:yield client,factory
    engine.dispose()

def team(c):
    r=c.post('/api/teams',json={'name':'Research'});assert r.status_code==201,r.text;return r.json()
def folder(c,name='inbox'):
    r=c.post('/api/files/folders',json={'name':name});assert r.status_code==201,r.text;return r.json()['id']
def invite(c,t,uid=2,role='editor'):
    r=c.post(f'/api/teams/{t["id"]}/members',json={'email':f'member{uid}@gmail.com','role':role});assert r.status_code==201,r.text;return r.json()['id']
def join(c,t,uid=2,role='editor'):
    iid=invite(c,t,uid,role);c.headers['x-user']=str(uid);r=c.post('/api/team-invitations/'+iid+'/accept');assert r.status_code==200,r.text;return iid
def request(c,parent=None,**changes):
    r=c.post('/api/file-requests',json={'title':'Project','parent_id':parent or folder(c),'expires_days':7,'max_file_size':64,'max_total_size':128,**changes});assert r.status_code==201,r.text;return r.json(),r.json()['url'].split('/r/')[1]

def test_explicit_invitation_and_namespace(env):
    c,_=env;t=team(c);tid=t['id'];root=t['root_id'];iid=invite(c,t)
    assert root not in [x['id'] for x in c.get('/api/files').json()['items']]
    c.headers['x-user']='2';assert c.get(f'/api/teams/{tid}/files').status_code==404
    assert c.get('/api/teams').json()['invitations'][0]['id']==iid
    assert c.post('/api/team-invitations/'+iid+'/accept').status_code==200
    assert c.get(f'/api/teams/{tid}/files').status_code==200
    assert c.get('/api/files/'+root).status_code==404
    c.headers['x-user']='3';assert c.post('/api/team-invitations/'+iid+'/accept').status_code==404

def test_member_scope_and_revoked_upload(env):
    c,_=env;private=folder(c,'private');t=team(c);tid=t['id'];join(c,t)
    assert c.get(f'/api/teams/{tid}/files?parent={private}').status_code==404
    fid=c.post(f'/api/teams/{tid}/folders',json={'name':'Docs'}).json()['id']
    assert c.patch(f'/api/teams/{tid}/files/{fid}',json={'parent_id':private}).status_code==404
    uid=c.post(f'/api/teams/{tid}/uploads',json={'name':'a','size':3}).json()['id']
    c.headers['x-user']='1';assert c.delete(f'/api/teams/{tid}/members/2').status_code==200
    c.headers['x-user']='2';assert c.put(f'/api/teams/{tid}/uploads/{uid}',content=b'abc',headers={'Upload-Offset':'0'}).status_code==404
    assert c.get(f'/api/teams/{tid}/files').status_code==404

def test_viewer_seats_and_personal_backdoors(env):
    c,_=env;t=team(c);tid=t['id'];join(c,t,role='viewer')
    assert c.post(f'/api/teams/{tid}/folders',json={'name':'no'}).status_code==403
    assert c.post(f'/api/teams/{tid}/members',json={'email':'member3@gmail.com'}).status_code==403
    c.headers['x-user']='1'
    for uid in (3,4,5):invite(c,t,uid)
    assert c.post(f'/api/teams/{tid}/members',json={'email':'member6@gmail.com'}).status_code==409
    node=c.post(f'/api/teams/{tid}/folders',json={'name':'Hidden'}).json()['id']
    assert c.get('/api/files/'+node).status_code==404
    assert c.post('/api/files/'+node+'/shares').status_code==404
    assert c.patch('/api/files/'+node,json={'parent_id':None}).status_code==404
    c.headers['x-user']='8';other=team(c)
    assert c.get(f'/api/teams/{other["id"]}/files?parent={node}').status_code==404

def test_team_expiry_keeps_read_and_management(env):
    c,factory=env;t=team(c);join(c,t);tid=t['id']
    assert c.post(f'/api/teams/{tid}/folders',json={'name':'Kept'}).status_code==201
    with factory() as db:db.get(User,1).plan_expires_at=utcnow()-timedelta(seconds=1);db.commit()
    assert c.get(f'/api/teams/{tid}/files').status_code==200
    assert c.post(f'/api/teams/{tid}/folders',json={'name':'blocked'}).status_code==403
    c.headers['x-user']='1';assert c.delete(f'/api/teams/{tid}/members/2').status_code==200
    assert c.get(f'/api/teams/{tid}/files').json()['items'][0]['name']=='Kept'

def test_team_bytes_shared_quota_and_trash_restore(env):
    c,_=env;t=team(c);tid=t['id'];join(c,t)
    r=c.post(f'/api/teams/{tid}/uploads',json={'name':'a.txt','size':3});assert r.status_code==201,r.text;uid=r.json()['id']
    assert c.put(f'/api/teams/{tid}/uploads/{uid}',content=b'abc',headers={'Upload-Offset':'0'}).status_code==200
    r=c.post(f'/api/teams/{tid}/uploads/{uid}/complete');assert r.status_code==200,r.text;node=r.json()['id']
    assert c.get(f'/api/teams/{tid}/files/{node}/download').content==b'abc'
    assert c.post(f'/api/teams/{tid}/files/{node}/trash').status_code==200
    assert c.get(f'/api/teams/{tid}/files?trash=true').json()['items'][0]['id']==node
    assert c.post(f'/api/teams/{tid}/files/{node}/restore').status_code==200
    c.headers['x-user']='1';assert c.get('/api/storage/usage').json()['used']==3
    assert c.get('/api/files/'+node+'/download').status_code==404

def test_request_upload_only_and_cross_tokens(env):
    c,_=env;row,token=request(c);_,other=request(c,folder(c,'other'));c.headers.pop('x-user')
    page=c.get('/r/'+token);assert page.status_code==200;assert 'script-src' in page.headers['content-security-policy']
    r=c.post(f'/api/requests/{token}/uploads',json={'name':'guest.txt','size':3});assert r.status_code==201,r.text;uid=r.json()['id']
    assert c.put(f'/api/requests/{token}/uploads/{uid}',content=b'abc',headers={'Upload-Offset':'0'}).status_code==200
    r=c.post(f'/api/requests/{token}/uploads/{uid}/complete');assert r.status_code==200,r.text
    assert r.json()=={'ok':True,'name':'guest.txt','size':3}
    assert c.get(f'/api/requests/{token}/files').status_code==404
    assert c.post(f'/api/requests/{other}/uploads/{uid}/complete').status_code==404
    assert c.get('/api/files').status_code==401
    c.headers['x-user']='1';node=c.get('/api/files?parent='+row['parent_id']).json()['items'][0]
    assert c.get('/api/files/'+node['id']+'/download').content==b'abc'

def test_request_budget_reservations_offsets_and_path(env):
    c,_=env;row,token=request(c)
    a=c.post(f'/api/requests/{token}/uploads',json={'name':'a','size':64}).json()['id']
    c.post(f'/api/requests/{token}/uploads',json={'name':'b','size':64})
    assert c.post(f'/api/requests/{token}/uploads',json={'name':'c','size':1}).status_code==413
    assert c.put(f'/api/requests/{token}/uploads/{a}',content=b'bad',headers={'Upload-Offset':'1'}).status_code==409
    assert c.delete(f'/api/requests/{token}/uploads/{a}').status_code==200
    assert c.post(f'/api/requests/{token}/uploads',json={'name':'../escape','size':1}).status_code==400
    assert c.post(f'/api/requests/{token}/uploads',json={'name':'huge','size':65}).status_code==413

def test_request_closure_and_downgrade_rechecked(env):
    c,factory=env;row,token=request(c)
    uid=c.post(f'/api/requests/{token}/uploads',json={'name':'pending','size':1}).json()['id']
    assert c.put(f'/api/requests/{token}/uploads/{uid}',content=b'x',headers={'Upload-Offset':'0'}).status_code==200
    assert c.delete('/api/file-requests/'+row['id']).status_code==200
    assert c.post(f'/api/requests/{token}/uploads/{uid}/complete').status_code==410
    _,token=request(c,folder(c,'next'))
    with factory() as db:db.get(User,1).plan_expires_at=utcnow()-timedelta(seconds=1);db.commit()
    assert c.get('/r/'+token).status_code==403
    assert c.post(f'/api/requests/{token}/uploads',json={'name':'new','size':0}).status_code==403

def test_request_targets_limits_and_owner_checks(env):
    c,_=env;t=team(c)
    assert c.post('/api/file-requests',json={'title':'no','parent_id':t['root_id']}).status_code==404
    target=folder(c)
    for extra in [{'expires_days':31},{'max_file_size':-1},{'max_total_size':2,'max_file_size':3}]:
        assert c.post('/api/file-requests',json={'title':'test','parent_id':target,**extra}).status_code in (400,422)
    row,_=request(c,target);c.headers['x-user']='2'
    assert c.delete('/api/file-requests/'+row['id']).status_code==404
    assert c.post('/api/file-requests',json={'title':'no','parent_id':target}).status_code==403


def test_group_versions_and_viewer_cannot_restore(env):
    c,_=env;t=team(c);tid=t['id']
    def send(data,replace=None):
        r=c.post(f'/api/teams/{tid}/uploads',json={'name':'a.txt','size':len(data),'replace_node_id':replace})
        assert r.status_code==201,r.text
        uid=r.json()['id']
        assert c.put(f'/api/teams/{tid}/uploads/{uid}',content=data,headers={'Upload-Offset':'0'}).status_code==200
        r=c.post(f'/api/teams/{tid}/uploads/{uid}/complete');assert r.status_code==200,r.text
        return r.json()['id']
    node=send(b'old');send(b'new',node)
    base=f'/api/teams/{tid}/files/{node}/versions'
    v=c.get(base).json()['items'][0]
    assert c.get(base+'/'+v['id']+'/download').content==b'old'
    # Even sponsor cannot access group data through the personal revision namespace.
    assert c.get('/api/files/'+node+'/versions').status_code==404
    join(c,t,role='viewer')
    assert c.get(base).json()['items'][0]['restorable'] is False
    assert c.post(base+'/'+v['id']+'/restore').status_code==403
    c.headers['x-user']='3';assert c.get(base).status_code==404
    c.headers['x-user']='1'
    assert c.post(base+'/'+v['id']+'/restore').status_code==200
    assert c.get(f'/api/teams/{tid}/files/{node}/download').content==b'old'


def test_group_paginated_search_does_not_include_personal(env):
    c,factory=env;t=team(c);tid=t['id'];folder(c,'personal')
    with factory() as db:
        db.add_all([FileNode(owner_id=1,parent_id=t['root_id'],name=f'f{i}',is_folder=True) for i in range(5)]);db.commit()
    first=c.get(f'/api/teams/{tid}/files?limit=2').json()
    assert first['has_more'] and first['next_offset']==2 and first['total_count']==5
    second=c.get(f'/api/teams/{tid}/files?limit=2&offset=2').json()
    assert not set(x['id'] for x in first['items']) & set(x['id'] for x in second['items'])
