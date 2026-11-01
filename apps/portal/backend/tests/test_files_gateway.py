import asyncio
import time
import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from legacy.gateways.files_gateway import API, COOKIE, Session, clean_path, create_app, properties

@pytest.mark.parametrize('path',['../secret','a/../b','a/./b','a//b','a\\b','x\x00','a/'+'x'*256])
def test_reject_unsafe_paths(path):
    with pytest.raises(HTTPException): clean_path(path)

def test_root_cannot_be_mutated():
    with pytest.raises(HTTPException): clean_path('/',False)
    assert clean_path('Đề bài/a%20b?#.txt') == 'Đề bài/a%20b?#.txt'

def response_xml(prefix='/remote.php/dav/files/alice',status='200 OK'):
    return f'''<d:multistatus xmlns:d="DAV:" xmlns:oc="http://owncloud.org/ns"><d:response><d:href>{prefix}/a.txt</d:href><d:propstat><d:prop><d:getcontentlength>12</d:getcontentlength><oc:permissions>R</oc:permissions></d:prop><d:status>HTTP/1.1 {status}</d:status></d:propstat></d:response></d:multistatus>'''.encode()

def test_only_successful_user_scoped_properties():
    assert properties(response_xml(),'/remote.php/dav/files/alice')[0]['path']=='a.txt'
    assert properties(response_xml('/remote.php/dav/files/bob'),'/remote.php/dav/files/alice')==[]
    assert properties(response_xml(status='404 Not Found'),'/remote.php/dav/files/alice')==[]
    with pytest.raises(HTTPException): properties(b'<!DOCTYPE x><x/>','/')

@pytest.fixture
def client():
    seen=[]
    def upstream(request):
        seen.append(request)
        if request.url.path=='/ocs/v2.php/cloud/user':
            return httpx.Response(200,json={'ocs':{'meta':{'statuscode':200},'data':{'id':'alice','display-name':'Alice'}}},headers={'set-cookie':'oc_session=never-forward'})
        if request.method=='GET' and '/shares' in request.url.path:
            return httpx.Response(200,json={'ocs':{'meta':{'statuscode':200},'data':[]}})
        if request.method=='GET': return httpx.Response(200,content=b'<script>bad()</script>',headers={'content-type':'image/svg+xml'})
        if request.method=='PROPFIND': return httpx.Response(207,content=response_xml())
        return httpx.Response(201)
    app=create_app(transport=httpx.MockTransport(upstream))
    with TestClient(app) as c:
        c.headers['origin']='http://testserver'
        token=c.get(API+'/session').json()['csrf']
        c.headers['x-csrf-token']=token
        c.seen=seen
        c.app_instance=app
        yield c

def logged(c):
    assert c.post(API+'/login',json={'username':'alice','password':'test-app-password'}).status_code==200

def test_authentication_and_csrf(client):
    assert client.get(API+'/list').status_code==401
    assert client.post(API+'/login',headers={'origin':'http://localhost:8000'},json={}).status_code==403
    assert client.post(API+'/login',headers={'x-csrf-token':'bad'},json={}).status_code==403
    logged(client)
    assert client.get(API+'/session').json()['authenticated'] is True
    assert client.cookies.get('oc_session') is None
    assert 'password' not in client.get(API+'/session').text

def test_destination_and_no_overwrite(client):
    logged(client)
    r=client.post(API+'/action',json={'op':'move','path':'a.txt','target':'Đề bài/a?#.txt'})
    assert r.status_code==200
    req=client.seen[-1]
    assert req.headers['destination']=='http://nextcloud/remote.php/dav/files/alice/%C4%90%E1%BB%81%20b%C3%A0i/a%3F%23.txt'
    assert req.headers['overwrite']=='F'
    assert not req.headers.get('cookie')
    assert client.post(API+'/action',json={'op':'delete','path':'/'}).status_code==400
    assert client.post(API+'/action',json={'op':'copy','path':'dir','target':'dir/child'}).status_code==400

def test_upload_refuses_replacement_and_preview_blocks_svg(client):
    logged(client)
    r=client.put(API+'/upload?path=a.txt',content=b'example')
    assert r.status_code==200 and client.seen[-1].headers['if-none-match']=='*'
    assert client.get(API+'/download?path=a.svg&preview=true').status_code==415
    r=client.get(API+'/download?path=a.svg')
    assert r.status_code==200 and 'attachment' in r.headers['content-disposition']
    assert r.headers['x-content-type-options']=='nosniff'

def test_share_query_is_preserved(client):
    logged(client)
    assert client.get(API+'/shares',params={'path':'a.txt'}).status_code==200
    assert client.seen[-1].url.params['path']=='/a.txt'
    assert client.seen[-1].url.params['format']=='json'

def test_expired_session_and_logout(client):
    logged(client)
    sid=client.cookies.get(COOKIE)
    client.app_instance.state.sessions[sid].expires=time.monotonic()-1
    assert client.get(API+'/list').status_code==401
    client.get(API+'/session')
    client.headers['x-csrf-token']=client.get(API+'/session').json()['csrf']
    logged(client)
    assert client.post(API+'/logout').status_code==200
    assert client.get(API+'/list').status_code==401

def test_no_arbitrary_proxy_and_bad_host(client):
    assert client.get(API+'/http://example.com').status_code==404
    assert client.get(API+'/session',headers={'host':'evil.example'}).status_code==400

def test_json_is_bounded_and_validated(client):
    assert client.post(API+'/login',content=b'{not json').status_code==400
    assert client.post(API+'/login',json=[]).status_code==400
    assert client.post(API+'/login',content=b'x'*8200).status_code==413

def test_restore_uses_special_virtual_target(client):
    logged(client)
    assert client.post(API+'/action',json={'op':'restore','path':'a.txt.d123'}).status_code==200
    req=client.seen[-1]
    assert '/trashbin/alice/restore/a.txt.d123' in req.headers['destination']
    assert req.headers['overwrite']=='T'

def test_user_credentials_are_not_shared_between_sessions(client):
    logged(client)
    client.get(API+'/list')
    alice_header=client.seen[-1].headers['authorization']
    original=client.cookies.get(COOKIE)
    client.cookies.clear()
    csrf=client.get(API+'/session').json()['csrf'];client.headers['x-csrf-token']=csrf
    client.post(API+'/login',json={'username':'bob','password':'different-password'})
    client.get(API+'/list')
    assert client.seen[-1].headers['authorization']!=alice_header
    assert client.app_instance.state.sessions[original].auth[0]=='alice'

def test_login_flow_uses_fixed_origin_and_rejects_untrusted_paths():
    def upstream(request):
        return httpx.Response(200,json={'login':'https://evil.example/steal','poll':{'endpoint':'http://evil.example/poll','token':'nope'}})
    with TestClient(create_app(transport=httpx.MockTransport(upstream))) as c:
        c.headers['origin']='http://testserver'
        c.headers['x-csrf-token']=c.get(API+'/session').json()['csrf']
        assert c.post(API+'/login/start').status_code==502

def test_partial_copy_is_not_reported_as_success():
    def upstream(request):
        return httpx.Response(207,content=b'<d:multistatus xmlns:d="DAV:"><d:response><d:status>HTTP/1.1 403 Forbidden</d:status></d:response></d:multistatus>')
    app=create_app(transport=httpx.MockTransport(upstream))
    with TestClient(app) as c:
        c.headers['origin']='http://testserver'
        c.headers['x-csrf-token']=c.get(API+'/session').json()['csrf']
        app.state.sessions[c.cookies.get(COOKIE)].auth=('alice','test')
        app.state.sessions[c.cookies.get(COOKIE)].uid='alice'
        assert c.post(API+'/action',json={'op':'copy','path':'folder','target':'other'}).status_code==403

def test_owned_tokens_are_revoked_but_borrowed_passwords_are_not(client):
    logged(client)
    assert client.post(API+'/logout').status_code==200
    assert not any(r.method=='DELETE' and r.url.path=='/ocs/v2.php/core/apppassword' for r in client.seen)
    client.headers['x-csrf-token']=client.get(API+'/session').json()['csrf']
    logged(client)
    client.app_instance.state.sessions[client.cookies.get(COOKIE)].delegated=True
    assert client.post(API+'/logout').status_code==200
    assert any(r.method=='DELETE' and r.url.path=='/ocs/v2.php/core/apppassword' for r in client.seen)
