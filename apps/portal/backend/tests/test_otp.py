"""Isolated identity tests: SQLite temporary DB; mocked delivery; no NC or network."""
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.models import Plan, User, utcnow
from app.core.security import hash_password, verify_password
from app.features.authentication.auth_models import PendingRegistration, AuthRateLimit, PasswordReset
from app.features.authentication import otp
from app.shared import mailer
from app.main import app

PASSWORD = "CloudBox-Test-93872!"
EMAIL = "cloudbox.otp.test@gmail.com"


@pytest.fixture
def env(tmp_path, monkeypatch):
    engine = create_engine("sqlite:///"+str(tmp_path/"identity.db"), connect_args={"check_same_thread": False, "timeout": 20})
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    with sessions() as db:
        db.add(Plan(code="free", name="Miễn phí", quota_gb=5, price_vnd=0, sort=0))
        db.commit()
    def dependency():
        with sessions() as db:
            yield db
    app.dependency_overrides[get_db] = dependency
    monkeypatch.setattr(settings, "base_url", "http://testserver")
    sent, resets = [], []
    monkeypatch.setattr(mailer, "send_verification_code", lambda email,name,code: sent.append((email,code)))
    monkeypatch.setattr(mailer, "send_password_reset", lambda email,name,link: resets.append((email,link)))
    client = TestClient(app, follow_redirects=False)
    yield client, sessions, sent, resets
    client.close()
    app.dependency_overrides.pop(get_db, None)
    engine.dispose()


def register(client, email=EMAIL):
    return client.post("/register", data={"email":email,"full_name":"OTP Test","password":PASSWORD,"password2":PASSWORD})


def age_send_limits(sessions):
    with sessions() as db:
        for row in db.query(AuthRateLimit).all():
            row.last_at = utcnow()-timedelta(seconds=61)
        for row in db.query(PendingRegistration).all():
            row.last_sent_at = utcnow()-timedelta(seconds=61)
        db.commit()


def add_user(sessions, email=EMAIL, verified=True):
    with sessions() as db:
        user = User(email=email, full_name="Existing", password_hash=hash_password(PASSWORD),
                    plan_id=db.query(Plan).one().id, role="user", is_verified=verified, is_active=True)
        db.add(user); db.commit()
        return user.id


def test_signup_is_pending_only_and_verification_has_no_nc(env):
    client,sessions,sent,_ = env
    response=register(client)
    assert response.status_code == 303 and response.headers["location"] == "/verify"
    assert sent[-1][0] == EMAIL and re.fullmatch(r"[0-9]{6}",sent[-1][1])
    with sessions() as db:
        assert db.query(User).count() == 0
        pending=db.query(PendingRegistration).one()
        assert pending.code_hash != sent[-1][1] and pending.attempts == 0
        assert verify_password(PASSWORD,pending.password_hash)
    assert sent[-1][1] not in response.text and PASSWORD not in response.text
    # PRG prevents browser refresh from resubmitting registration or sending mail.
    assert client.get("/verify").status_code == 200
    assert client.get("/verify").status_code == 200 and len(sent) == 1
    response=client.post("/verify", data={"code":sent[-1][1]})
    assert response.status_code == 303 and response.headers["location"] == "/dashboard"
    with sessions() as db:
        user=db.query(User).one()
        assert user.is_verified and user.nc_username is None and verify_password(PASSWORD,user.password_hash)
        pending=db.query(PendingRegistration).one()
        assert pending.consumed_at and pending.code_hash is None and pending.password_hash == ""
    # Same code and cookie can no longer activate another account.
    assert client.post("/verify",data={"code":sent[-1][1]}).headers["location"] == "/register"


@pytest.mark.parametrize("email",["a@outlook.com","a@yahoo.com","a@gmail.com.attacker.test","a@notgmail.com","a@googlemail.com","a@@gmail.com"])
def test_new_signup_only_accepts_exact_gmail(env,email):
    client,sessions,sent,_=env
    assert register(client,email).status_code==400
    assert not sent
    with sessions() as db:
        assert db.query(User).count()==db.query(PendingRegistration).count()==0


def test_resend_is_bound_cooldown_and_invalidates_old_code(env):
    client,sessions,sent,_=env
    register(client);old=sent[-1][1]
    assert client.post("/resend",data={"email":"attacker@gmail.com"}).status_code==429
    assert len(sent)==1
    age_send_limits(sessions)
    response=client.post("/resend",data={"email":"attacker@gmail.com"})
    assert response.status_code==303 and response.headers["location"]=="/verify"
    assert sent[-1][0]==EMAIL and len(sent)==2
    with sessions() as db:
        pending=db.query(PendingRegistration).one()
        assert pending.code_hash == otp.digest("otp:"+pending.id+":"+sent[-1][1])
    if old != sent[-1][1]:
        assert client.post("/verify",data={"code":old}).status_code==400
    assert client.post("/verify",data={"code":sent[-1][1]}).headers["location"]=="/dashboard"


def test_resend_hour_limit_survives_new_signup_and_cookies(env):
    client,sessions,sent,_=env
    for _ in range(5):
        age_send_limits(sessions)
        register(client)
    assert len(sent)==5
    age_send_limits(sessions)
    assert register(client).status_code==429
    assert len(sent)==5


def test_attempt_limit_and_expiry(env):
    client,sessions,sent,_=env
    register(client);code=sent[-1][1]
    wrong="999999" if code!="999999" else "111111"
    for _ in range(5):
        assert client.post("/verify",data={"code":wrong}).status_code==400
    assert client.post("/verify",data={"code":code}).status_code==400
    age_send_limits(sessions)
    client.post("/resend")
    with sessions() as db:
        db.query(PendingRegistration).one().code_expires_at=utcnow()-timedelta(seconds=1);db.commit()
    assert client.post("/verify",data={"code":sent[-1][1]}).status_code==400
    with sessions() as db:
        assert db.query(User).count()==0


def test_cannot_verify_another_browser_pending(env):
    client,sessions,sent,_=env
    register(client)
    anonymous=TestClient(app,follow_redirects=False)
    assert anonymous.post("/verify",data={"code":sent[-1][1]}).headers["location"]=="/register"
    assert anonymous.post("/resend",data={"email":EMAIL}).headers["location"]=="/register"
    anonymous.close()


def test_smtp_failure_is_not_claimed_as_delivery(env,monkeypatch):
    client,sessions,sent,_=env
    def unavailable(*args):
        raise mailer.MailDeliveryError("internal secret must not reach response")
    monkeypatch.setattr(mailer,"send_verification_code",unavailable)
    response=register(client)
    assert response.status_code==503
    assert "internal secret" not in response.text
    with sessions() as db:
        assert db.query(User).count()==0
        assert db.query(PendingRegistration).one().code_hash is None


def test_return_to_signup_abandons_pending_without_accounts(env):
    client,sessions,sent,_=env
    register(client)
    client.get("/register")
    assert client.post("/verify",data={"code":sent[-1][1]}).headers["location"]=="/register"
    age_send_limits(sessions)
    assert register(client,"correct.address@gmail.com").status_code==303
    with sessions() as db:
        assert db.query(User).count()==0


def test_existing_non_gmail_verified_login_preserves_hash(env):
    client,sessions,_,_=env
    uid=add_user(sessions,"legacy@example.com")
    with sessions() as db:
        before=db.get(User,uid).password_hash
    response=client.post("/login",data={"email":"legacy@example.com","password":PASSWORD})
    assert response.headers["location"]=="/dashboard"
    with sessions() as db:
        assert db.get(User,uid).password_hash==before


def test_legacy_unverified_login_continues_verification(env):
    client,sessions,sent,_=env
    uid=add_user(sessions,"legacy@example.com",verified=False)
    response=client.post("/login",data={"email":"legacy@example.com","password":PASSWORD})
    assert response.status_code==303 and response.headers["location"]=="/verify"
    assert sent[-1][0]=="legacy@example.com"
    assert client.post("/verify",data={"code":sent[-1][1]}).headers["location"]=="/dashboard"
    with sessions() as db:
        assert db.query(User).count()==1 and db.get(User,uid).is_verified


def test_verified_account_cannot_be_replaced_by_registration(env):
    client,sessions,_,_=env
    uid=add_user(sessions)
    assert register(client).status_code==400
    with sessions() as db:
        assert db.query(User).count()==1 and db.get(User,uid).full_name=="Existing"


def test_concurrent_code_consumption_only_activates_once(env):
    client,sessions,sent,_=env
    register(client)
    cookies=dict(client.cookies)
    # Avoid app startup/lifespan which accesses the application's engine.
    def request_once(_):
        other=TestClient(app,follow_redirects=False);other.cookies.update(cookies)
        response=other.post("/verify",data={"code":sent[-1][1]});other.close()
        return response.headers.get("location")
    with ThreadPoolExecutor(max_workers=2) as pool:
        locations=list(pool.map(request_once,range(2)))
    assert sorted(locations)==["/dashboard","/register"]
    with sessions() as db:
        assert db.query(User).count()==1


def test_password_recovery_single_use_and_no_account_enumeration(env):
    client,sessions,_,resets=env
    uid=add_user(sessions,"legacy@example.com")
    existing=client.post("/forgot-password",data={"email":"legacy@example.com"})
    age_send_limits(sessions)
    unknown=client.post("/forgot-password",data={"email":"missing@example.com"})
    assert existing.status_code==unknown.status_code==200
    assert existing.text==unknown.text
    token=resets[-1][1].split("token=",1)[1]
    assert client.get("/reset-password",params={"token":token}).headers["referrer-policy"]=="no-referrer"
    new="CloudBox-New-Password-987"
    assert client.post("/reset-password",data={"token":token,"password":new,"password2":new}).status_code==200
    assert client.post("/reset-password",data={"token":token,"password":new,"password2":new}).status_code==400
    with sessions() as db:
        assert verify_password(new,db.get(User,uid).password_hash)
        assert not verify_password(PASSWORD,db.get(User,uid).password_hash)
        assert db.query(PasswordReset).one().consumed_at


def test_cross_origin_rejected(env):
    client,_,sent,_=env
    response=client.post("/register",headers={"Origin":"https://attacker.test"},
                         data={"email":EMAIL,"full_name":"Test","password":PASSWORD,"password2":PASSWORD})
    assert response.status_code==403 and not sent


def test_mailer_never_logs_codes_when_unconfigured(monkeypatch,caplog):
    monkeypatch.setattr(settings,"smtp_host","")
    with pytest.raises(mailer.MailDeliveryError):
        mailer.send_mail(EMAIL,"Verify","Secret code 654321")
    assert "654321" not in caplog.text


def test_mailpit_is_development_only(monkeypatch):
    monkeypatch.setattr(settings,"smtp_host","mailpit")
    monkeypatch.setattr(settings,"mail_from","CloudBox <no-reply@cloudbox.local>")
    monkeypatch.delenv("MAIL_DELIVERY_MODE",raising=False)
    assert not mailer.delivery_configured()
    monkeypatch.setenv("MAIL_DELIVERY_MODE","development")
    assert mailer.delivery_configured()
