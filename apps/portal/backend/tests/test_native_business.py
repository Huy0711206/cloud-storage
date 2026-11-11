"""Business regression against new identities/native storage, never production.

Temporary SQLite, no app lifespan, mocked receipt; outbound HTTP fails the test.
Payment callbacks here are signed local simulations, not real VNPay payments.
"""
from datetime import timedelta
from urllib.parse import parse_qsl, urlparse

import pytest
import httpx
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.core.config import settings
from app.core.models import Plan, User, Order, utcnow
from app.core.security import hash_password, verify_password
from app.features.billing import service as billing
from app.features.payments import vnpay
from app.shared import mailer
from app.main import app

PASSWORD="Native-Business-Secret-827!"
USER_EMAIL="legacy.business@example.com"
ADMIN_EMAIL="admin.business@example.com"


@pytest.fixture
def business(tmp_path,monkeypatch):
    engine=create_engine("sqlite:///"+str(tmp_path/"business.db"),connect_args={"check_same_thread":False})
    Base.metadata.create_all(engine)
    sessions=sessionmaker(bind=engine,expire_on_commit=False)
    with sessions() as db:
        free=Plan(code="free",name="Miễn phí",quota_gb=5,price_vnd=0,sort=0)
        basic=Plan(code="basic",name="Cơ bản",quota_gb=100,price_vnd=39000,sort=1)
        standard=Plan(code="standard",name="Tiêu chuẩn",quota_gb=500,price_vnd=89000,sort=2)
        db.add_all([free,basic,standard]);db.flush()
        db.add_all([
            User(email=USER_EMAIL,full_name="Existing paid customer",password_hash=hash_password(PASSWORD),
                 is_active=True,is_verified=True,role="user",plan_id=free.id,nc_username=USER_EMAIL),
            User(email=ADMIN_EMAIL,full_name="Administrator",password_hash=hash_password(PASSWORD),
                 is_active=True,is_verified=True,role="admin"),
            User(email="other.business@gmail.com",full_name="Other",password_hash=hash_password(PASSWORD),
                 is_active=True,is_verified=True,role="user",plan_id=free.id),
        ]);db.commit()
    def db_override():
        with sessions() as db: yield db
    app.dependency_overrides[get_db]=db_override
    monkeypatch.setattr(settings,"base_url","http://testserver")
    monkeypatch.setattr(settings,"vnpay_tmn_code","TEST-NATIVE")
    monkeypatch.setattr(settings,"vnpay_hash_secret","isolated-native-callback-key")
    monkeypatch.setattr(settings,"vnpay_pay_url","https://sandbox.vnpayment.vn/paymentv2/vpcpay.html")
    monkeypatch.setenv("STORAGE_ROOT",str(tmp_path/"blobs"))
    receipts=[]
    monkeypatch.setattr(mailer,"send_receipt",lambda *args: receipts.append(args))
    original_send=httpx.Client.send
    def local_send(client,request,*args,**kwargs):
        if request.url.host != "testserver":
            raise AssertionError("Native business flow attempted outbound HTTP")
        return original_send(client,request,*args,**kwargs)
    monkeypatch.setattr(httpx.Client,"send",local_send)
    client=TestClient(app,follow_redirects=False)
    yield client,sessions,receipts
    client.close();app.dependency_overrides.pop(get_db,None);engine.dispose()


def login(client,email=USER_EMAIL,password=PASSWORD):
    return client.post("/login",data={"email":email,"password":password})


def order(sessions):
    with sessions() as db:
        return db.query(Order).order_by(Order.id.desc()).first()


def callback(row,amount=None,code="00"):
    params={"vnp_Amount":str(row.amount_vnd*100 if amount is None else amount),
            "vnp_BankCode":"NCB","vnp_ResponseCode":code,"vnp_TransactionStatus":code,
            "vnp_TmnCode":"TEST-NATIVE","vnp_TransactionNo":"NATIVE-LOCAL-001",
            "vnp_TxnRef":row.txn_ref,"vnp_OrderInfo":"CloudBox isolated test",
            "vnp_PayDate":"20261108120000"}
    params["vnp_SecureHash"]=vnpay.sign(params,settings.vnpay_hash_secret)
    return params


@pytest.mark.parametrize("months,multiplier",[(1,1),(3,3),(12,10)])
def test_checkout_uses_current_database_price_and_period(business,months,multiplier):
    client,sessions,_=business
    assert login(client).headers["location"]=="/dashboard"
    response=client.post("/billing/checkout",data={"plan_code":"basic","months":months})
    assert response.status_code==303
    url=urlparse(response.headers["location"])
    params=dict(parse_qsl(url.query))
    assert url.netloc=="sandbox.vnpayment.vn" and vnpay.verify_response(params)
    assert params["vnp_Amount"]==str(39000*multiplier*100)
    assert params["vnp_ReturnUrl"]=="http://testserver/billing/vnpay/return"
    row=order(sessions)
    assert row.amount_vnd==39000*multiplier and row.status=="pending" and row.months==months


def test_signed_payment_applies_plan_once_without_nextcloud(business):
    client,sessions,receipts=business
    login(client)
    client.post("/billing/checkout",data={"plan_code":"basic","months":3})
    row=order(sessions);params=callback(row)
    response=client.get("/billing/vnpay/return",params=params)
    assert response.status_code==200
    with sessions() as db:
        user=db.query(User).filter_by(email=USER_EMAIL).one()
        expiry=user.plan_expires_at
        assert user.plan.quota_gb==100 and user.quota_synced
        assert utcnow()+timedelta(days=89)<expiry<utcnow()+timedelta(days=91)
        assert db.get(Order,row.id).status=="paid"
    assert len(receipts)==1
    ipn=client.get("/billing/vnpay/ipn",params=params)
    assert ipn.json()["RspCode"]=="02"
    assert client.get("/billing/vnpay/return",params=params).status_code==200
    with sessions() as db:
        assert db.query(User).filter_by(email=USER_EMAIL).one().plan_expires_at==expiry
        assert db.query(Order).count()==1
    assert len(receipts)==1


def test_amount_and_signature_tampering_never_upgrades(business):
    client,sessions,receipts=business
    login(client);client.post("/billing/checkout",data={"plan_code":"basic","months":1})
    row=order(sessions)
    signed_wrong_amount=callback(row,amount=100)
    assert client.get("/billing/vnpay/ipn",params=signed_wrong_amount).json()["RspCode"]=="04"
    params=callback(row);params["vnp_Amount"]="100"
    assert client.get("/billing/vnpay/ipn",params=params).json()["RspCode"]=="97"
    with sessions() as db:
        assert db.get(Order,row.id).status=="pending"
        assert db.query(User).filter_by(email=USER_EMAIL).one().plan.code=="free"
    assert not receipts


def test_failed_callback_keeps_free_plan(business):
    client,sessions,receipts=business
    login(client);client.post("/billing/checkout",data={"plan_code":"basic","months":1})
    row=order(sessions)
    assert client.get("/billing/vnpay/ipn",params=callback(row,code="24")).json()["RspCode"]=="00"
    with sessions() as db:
        assert db.get(Order,row.id).status=="failed"
        assert db.query(User).filter_by(email=USER_EMAIL).one().plan.code=="free"
    assert not receipts


def test_admin_grant_renew_expire_and_sync_native_quota(business):
    client,sessions,_=business
    assert login(client,ADMIN_EMAIL).headers["location"]=="/admin"
    with sessions() as db:
        uid=db.query(User).filter_by(email=USER_EMAIL).one().id
    for _ in range(2):
        response=client.post(f"/admin/users/{uid}/grant",data={"plan_code":"basic","months":1})
        assert response.status_code==303
    with sessions() as db:
        user=db.get(User,uid)
        assert user.plan.quota_gb==100 and user.quota_synced
        assert utcnow()+timedelta(days=59)<user.plan_expires_at<utcnow()+timedelta(days=61)
        user.plan_expires_at=utcnow()-timedelta(seconds=1);db.commit()
        assert billing.run_maintenance(db)==1
        db.expire_all();user=db.get(User,uid)
        assert user.plan.code=="free" and user.plan_expires_at is None and user.quota_synced
    assert client.post(f"/admin/users/{uid}/sync").status_code==303


def test_non_admin_cannot_grant_or_change_prices(business):
    client,sessions,_=business
    login(client)
    with sessions() as db:
        uid=db.query(User).filter_by(email="other.business@gmail.com").one().id
        plan_id=db.query(Plan).filter_by(code="basic").one().id
    assert client.post(f"/admin/users/{uid}/grant",data={"plan_code":"basic","months":12}).status_code==403
    assert client.post(f"/admin/plans/{plan_id}",data={"name":"Cheap","price_vnd":1,"quota_gb":999}).status_code==403
    with sessions() as db:
        assert db.get(User,uid).plan.code=="free"
        assert db.get(Plan,plan_id).price_vnd==39000


def test_admin_lock_blocks_existing_session_and_keeps_account(business):
    client,sessions,_=business
    login(client)
    cookies=dict(client.cookies)
    login(client,ADMIN_EMAIL)
    with sessions() as db:
        uid=db.query(User).filter_by(email=USER_EMAIL).one().id
    assert client.post(f"/admin/users/{uid}/toggle").status_code==303
    other=TestClient(app,follow_redirects=False);other.cookies.update(cookies)
    assert other.get("/dashboard").headers["location"]=="/login"
    assert other.post("/login",data={"email":USER_EMAIL,"password":PASSWORD}).status_code==400
    assert client.post(f"/admin/users/{uid}/toggle").status_code==303
    assert other.post("/login",data={"email":USER_EMAIL,"password":PASSWORD}).headers["location"]=="/dashboard"
    other.close()
    with sessions() as db:
        assert db.get(User,uid).email==USER_EMAIL and db.get(User,uid).is_active


def test_password_change_uses_cloudbox_hash_only(business):
    client,sessions,_=business
    login(client)
    new="New-Native-Password-82731"
    client.post("/account/password",data={"current":"incorrect","new":new,"new2":new})
    with sessions() as db:
        assert verify_password(PASSWORD,db.query(User).filter_by(email=USER_EMAIL).one().password_hash)
    response=client.post("/account/password",data={"current":PASSWORD,"new":new,"new2":new})
    assert response.status_code==303
    with sessions() as db:
        user=db.query(User).filter_by(email=USER_EMAIL).one()
        assert verify_password(new,user.password_hash) and not verify_password(PASSWORD,user.password_hash)
    client.post("/logout")
    assert login(client,password=new).headers["location"]=="/dashboard"
    assert login(client,password=PASSWORD).status_code==400


def test_admin_pages_never_expose_password_hashes(business):
    client,sessions,_=business
    login(client,ADMIN_EMAIL)
    with sessions() as db:
        hashes=[u.password_hash for u in db.query(User)]
    for path in ("/admin","/admin/users","/admin/orders","/admin/plans"):
        response=client.get(path)
        assert response.status_code==200
        assert all(value not in response.text for value in hashes)


def test_activation_failure_rolls_back_paid_order_and_allows_retry(business,monkeypatch):
    from app.features.payments import service as payment
    client,sessions,receipts=business
    login(client);client.post("/billing/checkout",data={"plan_code":"basic","months":1})
    row=order(sessions);params=callback(row)
    actual_activate=payment.activate_plan
    def interrupted_activation(db,user,plan,months,**kwargs):
        actual_activate(db,user,plan,months,commit=False)
        db.flush()  # Prove rollback even after SQL for both order and user reached SQLite.
        raise RuntimeError("injected interruption before commit")
    monkeypatch.setattr(payment,"activate_plan",interrupted_activation)
    with pytest.raises(RuntimeError,match="injected interruption"):
        with sessions() as db:
            payment.process_payment(db,params)
    with sessions() as db:
        saved=db.get(Order,row.id)
        user=db.query(User).filter_by(email=USER_EMAIL).one()
        assert saved.status=="pending" and saved.paid_at is None and saved.gateway_txn_no is None
        assert user.plan.code=="free" and user.plan_expires_at is None
    monkeypatch.setattr(payment,"activate_plan",actual_activate)
    assert client.get("/billing/vnpay/ipn",params=params).json()["RspCode"]=="00"
    with sessions() as db:
        assert db.get(Order,row.id).status=="paid"
        assert db.query(User).filter_by(email=USER_EMAIL).one().plan.code=="basic"
    assert len(receipts)==1


def test_historical_versions_restricted_to_owner_and_exact_node(business):
    import hashlib
    from app.features.storage.native_models import FileNode,identifier
    from app.features.storage.migration_models import FileVersion
    from app.features.storage.native_service import blob_path
    client,sessions,_=business
    login(client)
    content=b"retained historical version bytes"
    key=identifier();path=blob_path(key);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(content)
    with sessions() as db:
        uid=db.query(User).filter_by(email=USER_EMAIL).one().id
        node=FileNode(owner_id=uid,name="document.txt",is_folder=False,size=0)
        other_node=FileNode(owner_id=uid,name="different.txt",is_folder=False,size=0)
        db.add_all([node,other_node]);db.flush()
        version=FileVersion(owner_id=uid,node_id=node.id,source_key="test-only:version:1",
                            name="document.txt",size=len(content),blob_key=key,
                            sha256=hashlib.sha256(content).hexdigest())
        db.add(version);db.commit()
        node_id,other_id,version_id=node.id,other_node.id,version.id
    listed=client.get(f"/api/files/{node_id}/versions")
    assert listed.status_code==200 and listed.json()["items"][0]["id"]==version_id
    assert "blob_key" not in listed.text and key not in listed.text
    download=client.get(f"/api/files/{node_id}/versions/{version_id}/download")
    assert download.status_code==200 and download.content==content
    assert "attachment" in download.headers["content-disposition"]
    assert client.get(f"/api/files/{other_id}/versions/{version_id}/download").status_code==404
    login(client,"other.business@gmail.com")
    assert client.get(f"/api/files/{node_id}/versions").status_code==404
    assert client.get(f"/api/files/{node_id}/versions/{version_id}/download").status_code==404
    client.post("/logout")
    assert client.get(f"/api/files/{node_id}/versions").status_code==401


def test_embedded_login_and_file_mutation_replay_form_body_with_csrf(business):
    import re,json
    client,sessions,_=business
    def token(response):
        hidden=re.search(r'name="csrf_token" value="([^"]+)"',response.text)
        if hidden:return hidden.group(1)
        payload=re.search(r'<script id="cloudbox-data" type="application/json">(.*?)</script>',response.text,re.S)
        return json.loads(payload.group(1))['csrf_token']
    csrf=token(client.get('/login'))
    headers={'Origin':'null','Sec-Fetch-Site':'same-origin'}
    response=client.post('/login',data={'email':USER_EMAIL,'password':PASSWORD,'csrf_token':csrf},headers=headers)
    assert response.status_code==303 and response.headers['location']=='/dashboard'
    csrf=token(client.get('/dashboard'))
    response=client.post('/api/files/folders',json={'name':'Embedded-browser-folder'},headers={**headers,'X-CSRF-Token':csrf})
    assert response.status_code==201


def test_native_business_fixture_blocks_outbound_http(business):
    with pytest.raises(AssertionError,match="outbound HTTP"):
        httpx.get("https://nextcloud.invalid")
