"""Origin is authoritative; Fetch Metadata is fallback for opaque/missing origins."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
import re
import json

def page_token(response):
    hidden=re.search(r'name="csrf_token" value="([^"]+)"',response.text)
    if hidden:return hidden.group(1)
    embedded=re.search(r'<script id="cloudbox-data" type="application/json">(.*?)</script>',response.text,re.S)
    return json.loads(embedded.group(1))['csrf_token']

@pytest.mark.parametrize('origin,site,status',[
    ('https://cloudbox.rachiba.top','same-origin',303),
    ('https://cloudbox.rachiba.top','cross-site',303),
    ('https://attacker.example','same-origin',403),
    ('https://attacker.example','cross-site',403),
    ('null','cross-site',403),
    (None,'cross-site',403),
])
def test_origin_validation_without_database_access(monkeypatch,origin,site,status):
    monkeypatch.setattr(settings,'base_url','https://cloudbox.rachiba.top')
    headers={'Sec-Fetch-Site':site}
    if origin is not None:headers['Origin']=origin
    client=TestClient(app,base_url='https://cloudbox.rachiba.top',follow_redirects=False)
    assert client.post('/logout',headers=headers).status_code==status
    client.close()

@pytest.mark.parametrize('via_header',[False,True])
def test_opaque_origin_with_session_bound_token_allowed(monkeypatch,via_header):
    monkeypatch.setattr(settings,'base_url','https://cloudbox.rachiba.top')
    client=TestClient(app,base_url=settings.base_url,follow_redirects=False)
    token=page_token(client.get('/login'))
    headers={'Origin':'null','Sec-Fetch-Site':'same-origin'}
    data={} if via_header else {'csrf_token':token}
    if via_header:headers['X-CSRF-Token']=token
    assert client.post('/logout',data=data,headers=headers).status_code==303
    client.close()

def test_opaque_token_cannot_be_reused_in_another_session(monkeypatch):
    monkeypatch.setattr(settings,'base_url','https://cloudbox.rachiba.top')
    client=TestClient(app,base_url=settings.base_url,follow_redirects=False)
    attacker=TestClient(app,base_url=settings.base_url,follow_redirects=False)
    token=page_token(client.get('/login'))
    page_token(attacker.get('/login'))
    assert attacker.post('/logout',data={'csrf_token':token},headers={'Origin':'null','Sec-Fetch-Site':'same-origin'}).status_code==403
    client.close();attacker.close()

@pytest.mark.parametrize('origin,site',[('https://attacker.example','same-origin'),('null','cross-site')])
def test_valid_csrf_does_not_allow_cross_origin_requests(monkeypatch,origin,site):
    monkeypatch.setattr(settings,'base_url','https://cloudbox.rachiba.top')
    client=TestClient(app,base_url=settings.base_url,follow_redirects=False)
    token=page_token(client.get('/login'))
    assert client.post('/logout',data={'csrf_token':token},headers={'Origin':origin,'Sec-Fetch-Site':site}).status_code==403
    client.close()
