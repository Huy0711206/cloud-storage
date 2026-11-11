"""Opt-in real row-lock regression tests; only a disposable cloudbox_qa database."""
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.core.models import User, Plan, Order, utcnow
from app.features.authentication import otp
from app.features.authentication.auth_models import PendingRegistration
from app.features.storage import native_service as storage
from app.features.storage.native_models import FileNode
from app.features.payments import service as payments, vnpay
from app.core.config import settings

@pytest.fixture
def pg(tmp_path,monkeypatch):
    url=os.environ.get('TEST_POSTGRES_URL','')
    if not url:pytest.skip('Disposable PostgreSQL was not supplied')
    if make_url(url).database!='cloudbox_qa':raise RuntimeError('Refusing a non-disposable database')
    engine=create_engine(url,pool_size=8)
    Base.metadata.drop_all(engine);Base.metadata.create_all(engine)
    sessions=sessionmaker(engine,expire_on_commit=False)
    monkeypatch.setenv('STORAGE_ROOT',str(tmp_path/'pg-blobs'))
    with sessions() as db:
        free=Plan(code='free',name='Free',quota_gb=1,price_vnd=0)
        paid=Plan(code='basic',name='Basic',quota_gb=100,price_vnd=39000)
        db.add_all([free,paid]);db.flush()
        user=User(email='pg-test@gmail.com',full_name='Disposable',password_hash='test-hash',is_verified=True,plan_id=free.id)
        db.add(user);db.commit();uid=user.id
    yield sessions,uid
    engine.dispose()

def race(function):
    barrier=Barrier(2)
    def run(_):barrier.wait();return function()
    with ThreadPoolExecutor(2) as pool:return list(pool.map(run,range(2)))

def test_otp_consumed_once_across_independent_pg_connections(pg):
    sessions,_=pg
    key='a'*64
    with sessions() as db:
        p=PendingRegistration(id=key,email='pg-test@gmail.com',full_name='Test',password_hash='hash',expires_at=utcnow()+timedelta(hours=1),code_expires_at=utcnow()+timedelta(minutes=10),attempts=0)
        p.code_hash=otp.digest('otp:'+key+':123456');db.add(p);db.commit()
    def attempt():
        with sessions() as db:
            otp.lock(db,'auth-identity')
            p=db.get(PendingRegistration,key)
            ok,_=otp.code_matches(p,'123456')
            if ok:p.consumed_at=utcnow()
            db.commit();return ok
    assert sorted(race(attempt))==[False,True]

def test_upload_quota_reservations_serialize_on_pg_user_row(pg):
    sessions,uid=pg
    with sessions() as db:
        db.add(FileNode(owner_id=uid,name='quota-accounting-fixture',is_folder=False,size=1024**3-8));db.commit()
    def reserve():
        with sessions() as db:
            user=db.get(User,uid)
            try:storage.start_upload(db,user,os.urandom(4).hex()+'.bin',None,6);return True
            except storage.StorageError:return False
    assert sorted(race(reserve))==[False,True]

def test_two_paid_orders_extend_same_user_without_losing_months(pg,monkeypatch):
    sessions,uid=pg
    monkeypatch.setattr(settings,'vnpay_hash_secret','pg-test-secret')
    monkeypatch.setattr(settings,'vnpay_tmn_code','PGTEST')
    params=[]
    with sessions() as db:
        plan=db.query(Plan).filter_by(code='basic').one()
        for i in range(2):
            order=Order(user_id=uid,plan_id=plan.id,months=1,amount_vnd=39000,txn_ref='pg-order-'+str(i));db.add(order)
            p={'vnp_TxnRef':order.txn_ref,'vnp_Amount':'3900000','vnp_ResponseCode':'00','vnp_TransactionStatus':'00','vnp_TmnCode':'PGTEST','vnp_TransactionNo':str(i)}
            p['vnp_SecureHash']=vnpay.sign(p,'pg-test-secret');params.append(p)
        db.commit()
    barrier=Barrier(2)
    def apply(p):
        barrier.wait()
        with sessions() as db:return payments.process_payment(db,p)[0]
    with ThreadPoolExecutor(2) as pool:assert list(pool.map(apply,params))==['00','00']
    with sessions() as db:
        user=db.get(User,uid)
        assert timedelta(days=59,hours=23)<user.plan_expires_at-utcnow()<=timedelta(days=60)
        assert db.query(Order).filter_by(status='paid').count()==2


def test_global_capacity_serializes_across_distinct_owners(pg,monkeypatch):
    sessions,uid=pg;monkeypatch.setenv('STORAGE_POOL_LIMIT_BYTES','10')
    with sessions() as db:
        first=db.get(User,uid)
        other=User(email='pg-other@gmail.com',full_name='Other',password_hash='unused',is_verified=True,plan_id=first.plan_id)
        db.add(other);db.commit();ids=iter([uid,other.id])
    def reserve():
        owner_id=next(ids)
        with sessions() as db:
            try:storage.start_upload(db,db.get(User,owner_id),'reserved',None,6);return True
            except storage.StorageError as exc:
                assert exc.status==507;return False
    assert sorted(race(reserve))==[False,True]


def test_concurrent_replacements_preserve_one_current_revision(pg):
    from app.features.storage.migration_models import FileVersion
    sessions,uid=pg
    with sessions() as db:
        user=db.get(User,uid);user.plan_id=db.query(Plan).filter_by(code='basic').one().id;db.commit()
        initial=storage.start_upload(db,user,'revision.txt',None,3)
        storage.append_chunk(db,user,initial['id'],b'old',0)
        node=storage.finish_upload(db,user,initial['id'])
        uploads=[]
        for data in (b'one',b'two'):
            item=storage.start_upload(db,user,'revision.txt',None,3,node['id'])
            storage.append_chunk(db,user,item['id'],data,0);uploads.append(item['id'])
    ids=iter(uploads)
    def finish():
        upload_id=next(ids)
        with sessions() as db:
            try:storage.finish_upload(db,db.get(User,uid),upload_id);return True
            except storage.StorageError as exc:
                assert exc.status==409;return False
    assert sorted(race(finish))==[False,True]
    with sessions() as db:
        assert db.query(FileVersion).count()==1
        assert storage.blob_path(db.get(FileNode,node['id']).blob_key).read_bytes() in (b'one',b'two')
