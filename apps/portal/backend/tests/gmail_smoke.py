"""One real SMTP verification, entirely disposable application DB/storage."""
import json,os,secrets
from fastapi.testclient import TestClient
from app.core.database import Base,engine,SessionLocal
from app.core.bootstrap import seed
from app.core.config import settings
from app.shared import mailer
from app.main import app
if engine.url.get_backend_name()!='sqlite' or not str(engine.url.database).startswith('/tmp/'):
    raise RuntimeError('Only temporary SQLite is allowed')
Base.metadata.create_all(engine)
with SessionLocal() as db:seed(db)
address=os.environ['SMTP_USER']
local,domain=address.rsplit('@',1)
if domain.lower()!='gmail.com':raise RuntimeError('Expected the configured Gmail sender')
email=local+'+cloudboxqa'+secrets.token_hex(3)+'@gmail.com'
password=secrets.token_urlsafe(24)+'-Aa7'
codes=[]
deliver=mailer.send_verification_code
def send(to,name,code):
    deliver(to,name,code)
    codes.append(code)  # Process memory only; never output or persisted.
mailer.send_verification_code=send
with TestClient(app,follow_redirects=False) as client:
    r=client.post('/register',data={'email':email,'full_name':'Kiểm thử CloudBox','password':password,'password2':password})
    assert r.status_code==303,(r.status_code,'Registration did not accept SMTP delivery')
    assert len(codes)==1
    r=client.post('/verify',data={'code':codes[0]})
    assert r.status_code==303 and r.headers['location']=='/dashboard'
    r=client.post('/api/uploads',json={'name':'smtp-flow-test.txt','size':15})
    assert r.status_code==201
    upload=r.json()['id']
    assert client.put('/api/uploads/'+upload,headers={'Upload-Offset':'0'},content=b'CloudBox native').status_code==200
    r=client.post('/api/uploads/'+upload+'/complete')
    assert r.status_code==200
    node=r.json()['id']
    assert client.get('/api/files/'+node+'/download').content==b'CloudBox native'
print(json.dumps({'smtp_accepted':True,'otp_consumed':True,'native_upload_download':True,'production_accounts_changed':False,'inbox_delivery_requires_user_confirmation':True}))
