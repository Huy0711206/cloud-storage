from test_native_storage import env, upload
from app.core.models import User
from app.features.storage.native_models import UploadSession
from app.features.storage.capacity import pool_usage


def test_global_pool_counts_pending_across_owners(env,monkeypatch):
    client,factory=env
    monkeypatch.setenv("STORAGE_POOL_LIMIT_BYTES","10")
    r=client.post("/api/uploads",json={"name":"first","size":7})
    assert r.status_code==201
    client.headers["x-test-user"]="2"
    assert client.post("/api/uploads",json={"name":"second","size":4}).status_code==507
    client.headers["x-test-user"]="1"
    assert client.delete("/api/uploads/"+r.json()["id"]).status_code==200
    client.headers["x-test-user"]="2"
    assert client.post("/api/uploads",json={"name":"second","size":4}).status_code==201


def test_trash_does_not_release_pool(env,monkeypatch):
    client,factory=env
    monkeypatch.setenv("STORAGE_POOL_LIMIT_BYTES","10")
    node,_=upload(client,data=b"1234567")
    assert client.post("/api/files/"+node["id"]+"/trash").status_code==200
    assert client.post("/api/uploads",json={"name":"next","size":4}).status_code==507
    with factory() as db:
        assert pool_usage(db)["used_bytes"]==7


def test_price_payload_uses_billing_calculation():
    from app.core.models import Plan
    from app.shared.frontend import plan as serialize
    from app.features.billing.service import calc_amount
    p=Plan(id=9,code='standard',name='Tiêu chuẩn',quota_gb=500,price_vnd=89000,is_active=True,sort=2)
    result=serialize(p)
    assert result['period_amounts']=={str(m):calc_amount(p,m) for m in (1,3,12)}
    assert result['period_amounts']=={'1':89000,'3':267000,'12':890000}


def test_approved_trial_catalog_keeps_prices():
    from app.features.billing.service import DEFAULT_PLANS
    assert [(row[0],row[2],row[3]) for row in DEFAULT_PLANS]==[('free',5,0),('basic',100,39000),('standard',500,89000),('premium',2048,199000)]
