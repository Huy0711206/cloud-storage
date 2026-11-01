"""CloudBox Files: a user-scoped Nextcloud client, never an admin proxy.

Opaque sessions and delegated app credentials live only in this process memory.
No Nextcloud cookies are forwarded in either direction. Run a single worker.
"""
import asyncio
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass, field
from http.cookiejar import CookieJar
import json
import os
from pathlib import Path
import re
import secrets
import time
from urllib.parse import quote, unquote, urlsplit
import xml.etree.ElementTree as ET

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.background import BackgroundTask
from starlette.middleware.trustedhost import TrustedHostMiddleware

COOKIE = 'cloudbox_files_session'
API = '/api/files'
MAX_UPLOAD = 2 * 1024 ** 3
NS = {'d': 'DAV:', 'oc': 'http://owncloud.org/ns', 'nc': 'http://nextcloud.org/ns'}
PROPS = '<d:resourcetype/><d:getcontentlength/><d:getcontenttype/><d:getlastmodified/><d:getetag/><d:quota-used-bytes/><d:quota-available-bytes/><oc:fileid/><oc:permissions/><oc:favorite/><oc:size/><nc:trashbin-filename/><nc:trashbin-original-location/><nc:trashbin-deletion-time/>'
FIND = f'<d:propfind xmlns:d="DAV:" xmlns:oc="{NS["oc"]}" xmlns:nc="{NS["nc"]}"><d:prop>{PROPS}</d:prop></d:propfind>'
ERRORS = {401:'Phiên truy cập Nextcloud đã hết hạn. Hãy đăng nhập lại.',403:'Bạn không có quyền thực hiện thao tác này.',404:'Tệp hoặc thư mục không còn tồn tại. Hãy làm mới danh sách.',405:'Tên này đã tồn tại hoặc thao tác không được hỗ trợ.',409:'Thư mục đích không tồn tại hoặc không hợp lệ.',412:'Tên này đã tồn tại. Hãy chọn tên khác.',413:'Tệp vượt giới hạn tải lên 2 GB.',423:'Tệp đang bị khóa. Hãy thử lại sau.',507:'Kho lưu trữ không còn đủ dung lượng.',429:'Có quá nhiều yêu cầu. Hãy chờ một lát.'}

class NoCookies(CookieJar):
    def extract_cookies(self, response, request): pass
    def set_cookie(self, cookie): pass

def clean_path(value: str, root: bool = True) -> str:
    if not isinstance(value, str) or len(value) > 2048 or '\\' in value or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise HTTPException(400, 'Đường dẫn không hợp lệ.')
    value = value.strip('/')
    if value and any(p in {'', '.', '..'} or len(p.encode()) > 255 for p in value.split('/')):
        raise HTTPException(400, 'Đường dẫn không hợp lệ.')
    if not root and not value:
        raise HTTPException(400, 'Cần chọn tệp hoặc thư mục cụ thể.')
    return value

def xml_tree(content: bytes):
    if len(content) > 16 * 1024 ** 2 or b'<!DOCTYPE' in content.upper() or b'<!ENTITY' in content.upper():
        raise HTTPException(502, 'Phản hồi danh sách không hợp lệ.')
    try: return ET.fromstring(content)
    except ET.ParseError: raise HTTPException(502, 'Không đọc được phản hồi Nextcloud.')

def properties(content: bytes, prefix: str):
    result = []
    for response in xml_tree(content).findall('d:response', NS):
        path = unquote(urlsplit(response.findtext('d:href', '', NS)).path).rstrip('/')
        if not path.startswith(prefix.rstrip('/') + '/') and path != prefix.rstrip('/'): continue
        props = {}
        for stat in response.findall('d:propstat', NS):
            if ' 200 ' not in stat.findtext('d:status', '', NS): continue
            prop = stat.find('d:prop', NS)
            if prop is not None: props.update({e.tag:e for e in prop})
        def get(key, default=''):
            e = props.get('{' + NS[key.split(':')[0]] + '}' + key.split(':')[1])
            return (e.text or default) if e is not None else default
        def num(key):
            try: return int(get(key, '0'))
            except ValueError: return 0
        if not props: continue
        rel = path[len(prefix.rstrip('/')):].strip('/')
        kind = props.get('{DAV:}resourcetype')
        folder = kind is not None and kind.find('d:collection', NS) is not None
        result.append({'path':rel,'name':get('nc:trashbin-filename') or rel.rsplit('/',1)[-1], 'folder':folder,
            'size':num('oc:size') if folder else num('d:getcontentlength'), 'mime':get('d:getcontenttype'),
            'modified':get('d:getlastmodified'),'etag':get('d:getetag'),'id':get('oc:fileid'),
            'permissions':get('oc:permissions'),'favorite':get('oc:favorite') == '1',
            'used':num('d:quota-used-bytes'),'available':num('d:quota-available-bytes'),
            'original':get('nc:trashbin-original-location'),'deleted':num('nc:trashbin-deletion-time')})
    return result

@dataclass
class Session:
    csrf: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    expires: float = field(default_factory=lambda: time.monotonic() + 8*3600)
    auth: tuple | None = None
    uid: str = ''
    name: str = ''
    delegated: bool = False
    poll_token: str = ''
    poll_path: str = ''
    poll_expires: float = 0
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

def create_app(upstream='http://nextcloud', public='http://localhost:8080', static_dir=None, transport=None):
    for url in (upstream, public):
        u = urlsplit(url)
        if u.scheme not in {'http','https'} or not u.hostname or u.username or u.password or u.path not in {'','/'} or u.query or u.fragment:
            raise ValueError('Nextcloud URL must be a fixed HTTP origin')
    upstream, public = upstream.rstrip('/'), public.rstrip('/')
    static_dir = Path(static_dir or Path(__file__).resolve().parents[2] / 'frontend' / 'dist-files')
    sessions: dict[str, Session] = {}
    attempts: dict[str, list] = {}
    async def forget(sid):
        s = sessions.pop(sid,None)
        if s and s.auth and s.delegated:
            try:
                await app.state.client.delete('/ocs/v2.php/core/apppassword',auth=s.auth,params={'format':'json'},timeout=8)
            except httpx.HTTPError: pass
    async def reap():
        while True:
            await asyncio.sleep(60)
            for sid,s in list(sessions.items()):
                if s.expires <= time.monotonic(): await forget(sid)
    @asynccontextmanager
    async def lifespan(app):
        async with httpx.AsyncClient(base_url=upstream, cookies=NoCookies(), follow_redirects=False,
                timeout=httpx.Timeout(300, connect=10), transport=transport,
                headers={'User-Agent':'CloudBox Files Preview','OCS-APIRequest':'true'}) as client:
            app.state.client = client
            task = asyncio.create_task(reap())
            try: yield
            finally:
                task.cancel()
                with suppress(asyncio.CancelledError): await task
                with suppress(TimeoutError):
                    async with asyncio.timeout(10):
                        await asyncio.gather(*(forget(sid) for sid in list(sessions)))
        sessions.clear()
    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=['localhost','127.0.0.1','testserver'])
    app.state.sessions = sessions

    @app.middleware('http')
    async def security(request, call_next):
        if request.method == 'POST':
            body = bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > 8192:
                    return JSONResponse({'detail':'Yêu cầu quá dài.'},413)
            request._body = bytes(body)
        if request.method not in {'GET','HEAD','OPTIONS'}:
            if request.headers.get('origin') != str(request.base_url).rstrip('/'):
                return JSONResponse({'detail':'Nguồn yêu cầu không hợp lệ.'},403)
            s = sessions.get(request.cookies.get(COOKIE,''))
            if not s or s.expires <= time.monotonic() or not secrets.compare_digest(request.headers.get('x-csrf-token',''), s.csrf):
                return JSONResponse({'detail':'Phiên đã hết hạn. Hãy tải lại trang.'},403)
        response = await call_next(request)
        response.headers.update({'X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer',
            'X-Frame-Options':'DENY','Cache-Control':'no-store',
            'Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; frame-src 'none'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"})
        return response

    def session(request, require=True):
        s = sessions.get(request.cookies.get(COOKIE,''))
        if not s or s.expires <= time.monotonic() or (require and not s.auth):
            raise HTTPException(401, ERRORS[401])
        return s

    async def payload(request):
        try: data = await request.json()
        except (ValueError, UnicodeDecodeError): raise HTTPException(400,'Yêu cầu không hợp lệ.')
        if not isinstance(data,dict): raise HTTPException(400,'Yêu cầu không hợp lệ.')
        return data

    async def call(method, path, s=None, **kwargs):
        try: r = await app.state.client.request(method, path, auth=s.auth if s else None, **kwargs)
        except httpx.HTTPError: raise HTTPException(502, 'Không kết nối được Nextcloud. Hãy thử lại.')
        if r.status_code >= 400:
            if r.status_code == 401 and s: s.auth = None
            raise HTTPException(r.status_code if r.status_code in ERRORS else 502, ERRORS.get(r.status_code,'Nextcloud chưa xử lý được yêu cầu. Hãy thử lại.'))
        if r.status_code == 207 and method in {'COPY','MOVE','DELETE'}:
            for node in xml_tree(r.content).findall('.//d:status',NS):
                match = re.search(r'\s([45]\d\d)\s',node.text or '')
                if match:
                    code = int(match.group(1))
                    raise HTTPException(code if code in ERRORS else 409,'Một phần thao tác chưa hoàn tất. '+ERRORS.get(code,'Hãy làm mới danh sách và kiểm tra quyền.'))
        return r

    async def ocs(path, s, method='GET', data=None, params=None):
        r = await call(method, path, s, params={'format':'json',**(params or {})}, data=data)
        try:
            payload = r.json()['ocs']
            code = int(payload['meta']['statuscode'])
            if code not in {100,200}: raise HTTPException(403, 'Nextcloud từ chối thao tác. Kiểm tra quyền hoặc chính sách chia sẻ.')
            return payload.get('data')
        except (KeyError, ValueError, TypeError): raise HTTPException(502,'Phản hồi Nextcloud không hợp lệ.')

    async def establish(s, username, password, delegated):
        candidate = Session(auth=(username,password))
        data = await ocs('/ocs/v2.php/cloud/user', candidate)
        uid = data.get('id','')
        if not uid or '/' in uid or '\\' in uid: raise HTTPException(502,'Không xác định được tài khoản Nextcloud.')
        s.auth, s.uid, s.name, s.delegated = candidate.auth, uid, data.get('display-name') or data.get('displayname') or uid, delegated
        s.poll_token = ''
        s.expires = time.monotonic() + 8*3600

    def rate(request):
        key = request.client.host if request.client else 'local'
        now = time.monotonic()
        for old in list(attempts):
            if not attempts[old] or attempts[old][-1] < now-60: attempts.pop(old)
        bucket = attempts.setdefault(key, [])
        bucket[:] = [x for x in bucket if x > now-60]
        if len(bucket) >= 10: raise HTTPException(429, ERRORS[429])
        bucket.append(now)

    def dav(s, path='', trash=False):
        prefix = f'/remote.php/dav/trashbin/{quote(s.uid,safe="")}/trash' if trash else f'/remote.php/dav/files/{quote(s.uid,safe="")}'
        return prefix + '/' + quote(clean_path(path), safe='/')

    @app.get('/healthz')
    async def health():
        await call('GET','/status.php')
        return {'status':'ok','variant':'files-preview'}

    @app.get(API+'/session')
    async def bootstrap(request: Request):
        now = time.monotonic()
        for sid in list(sessions):
            if sessions[sid].expires <= now: await forget(sid)
        sid = request.cookies.get(COOKIE,'')
        if sid not in sessions:
            if len(sessions) >= 256: raise HTTPException(503,'Có quá nhiều phiên. Hãy thử lại sau.')
            sid = secrets.token_urlsafe(32)
            sessions[sid] = Session(expires=now+20*60)
        s = sessions[sid]
        response = JSONResponse({'csrf':s.csrf,'authenticated':bool(s.auth),'name':s.name if s.auth else '', 'uid':s.uid if s.auth else '', 'nextcloud':public})
        response.set_cookie(COOKIE,sid,httponly=True,samesite='strict',secure=request.url.scheme=='https',path=API)
        return response

    @app.post(API+'/login/start')
    async def start(request: Request):
        rate(request)
        s = session(request,False)
        if s.auth: raise HTTPException(409,'Bạn đã đăng nhập.')
        r = await call('POST','/index.php/login/v2')
        try:
            data = r.json()
            login = urlsplit(data['login']).path
            poll = urlsplit(data['poll']['endpoint']).path
            if not re.fullmatch(r'/(?:index\.php/)?login/v2/flow/[A-Za-z0-9_-]+',login) or not re.fullmatch(r'/(?:index\.php/)?login/v2/poll',poll): raise ValueError()
            s.poll_token, s.poll_path, s.poll_expires = data['poll']['token'], poll, time.monotonic()+20*60
            return {'login':public+login}
        except (ValueError,KeyError,TypeError): raise HTTPException(502,'Không khởi tạo được đăng nhập Nextcloud.')

    @app.post(API+'/login/poll')
    async def poll(request: Request):
        s = session(request,False)
        async with s.lock:
            if s.auth: return {'authenticated':True}
            if not s.poll_token or s.poll_expires <= time.monotonic(): raise HTTPException(400,'Lượt đăng nhập đã hết hạn. Hãy bắt đầu lại.')
            try: r = await app.state.client.post(s.poll_path, data={'token':s.poll_token})
            except httpx.HTTPError: raise HTTPException(502,'Không kết nối được Nextcloud.')
            if r.status_code == 404: return {'authenticated':False}
            if r.status_code != 200: raise HTTPException(502,'Không hoàn tất được đăng nhập.')
            try: data = r.json(); await establish(s,data['loginName'],data['appPassword'],True)
            except (ValueError,KeyError,TypeError): raise HTTPException(502,'Phản hồi đăng nhập không hợp lệ.')
            return {'authenticated':True}

    @app.post(API+'/login')
    async def login(request: Request):
        """Optional app-password login, useful when browser delegation is unavailable."""
        rate(request)
        s = session(request,False)
        if s.auth: raise HTTPException(409,'Bạn đã đăng nhập.')
        if int(request.headers.get('content-length','0')) > 4096: raise HTTPException(413,'Yêu cầu quá dài.')
        data = await payload(request)
        user, password = data.get('username',''),data.get('password','')
        if not isinstance(user,str) or not isinstance(password,str) or not user or not password or len(user)>320 or len(password)>1024: raise HTTPException(400,'Nhập tài khoản và mật khẩu ứng dụng.')
        await establish(s,user,password,False)
        return {'authenticated':True}

    @app.post(API+'/logout')
    async def logout(request: Request):
        session(request,False)
        await forget(request.cookies.get(COOKIE,''))
        response = JSONResponse({'ok':True})
        response.delete_cookie(COOKIE,path=API)
        return response

    @app.get(API+'/list')
    async def listing(request: Request, path: str='', view: str='files'):
        s = session(request)
        path = clean_path(path)
        if view not in {'files','favorites','trash'}: raise HTTPException(400,'Chế độ xem không hợp lệ.')
        trash = view == 'trash'
        if view != 'files' and path: raise HTTPException(400,'Chế độ này chỉ hỗ trợ thư mục gốc.')
        prefix = unquote(dav(s,'',trash)).rstrip('/')
        method, body = 'PROPFIND',FIND
        if view == 'favorites':
            method = 'REPORT'
            body = f'<oc:filter-files xmlns:d="DAV:" xmlns:oc="{NS["oc"]}" xmlns:nc="{NS["nc"]}"><oc:filter-rules><oc:favorite>1</oc:favorite></oc:filter-rules><d:prop>{PROPS}</d:prop></oc:filter-files>'
        r = await call(method,dav(s,path,trash),s,headers={'Depth':'1','Content-Type':'application/xml'},content=body.encode())
        all_items = properties(r.content,prefix)
        current = next((x for x in all_items if x['path']==path),{})
        entries = [x for x in all_items if x['path'] != path]
        quota = await call('PROPFIND',dav(s),s,headers={'Depth':'0','Content-Type':'application/xml'},content=FIND.encode())
        root = next(iter(properties(quota.content,unquote(dav(s)).rstrip('/'))),{})
        return {'items':entries,'permissions':current.get('permissions',''),'used':root.get('used',0),'available':root.get('available',0),'path':path,'view':view}

    @app.post(API+'/action')
    async def action(request: Request):
        s = session(request)
        if int(request.headers.get('content-length','0')) > 8192: raise HTTPException(413,'Yêu cầu quá dài.')
        data = await payload(request)
        op = data.get('op')
        path = clean_path(data.get('path',''),False)
        if op == 'mkdir': await call('MKCOL',dav(s,path),s)
        elif op == 'delete': await call('DELETE',dav(s,path),s)
        elif op in {'move','copy'}:
            target = clean_path(data.get('target',''),False)
            if target == path or target.startswith(path+'/'): raise HTTPException(400,'Thư mục đích không hợp lệ.')
            await call(op.upper(),dav(s,path),s,headers={'Destination':upstream+dav(s,target),'Overwrite':'F'})
        elif op == 'favorite':
            body = f'<d:propertyupdate xmlns:d="DAV:" xmlns:oc="{NS["oc"]}"><d:set><d:prop><oc:favorite>{1 if data.get("value") is True else 0}</oc:favorite></d:prop></d:set></d:propertyupdate>'
            r = await call('PROPPATCH',dav(s,path),s,content=body.encode(),headers={'Content-Type':'application/xml'})
            if any(' 200 ' not in x.text for x in xml_tree(r.content).findall('.//d:status',NS) if x.text): raise HTTPException(403,ERRORS[403])
        elif op == 'restore':
            # Nextcloud 35's virtual restore target needs T. Trashbin::restore
            # chooses a unique filename; ordinary MOVE/COPY still always use F.
            await call('MOVE',dav(s,path,True),s,headers={'Destination':upstream+f'/remote.php/dav/trashbin/{quote(s.uid,safe="")}/restore/'+quote(path,safe='/'),'Overwrite':'T'})
        else: raise HTTPException(400,'Thao tác không được hỗ trợ.')
        return {'ok':True}

    @app.put(API+'/upload')
    async def upload(request: Request, path: str):
        s = session(request)
        path = clean_path(path,False)
        if int(request.headers.get('content-length','0')) > MAX_UPLOAD: raise HTTPException(413,ERRORS[413])
        async def chunks():
            total = 0
            async for chunk in request.stream():
                total += len(chunk)
                if total > MAX_UPLOAD: raise HTTPException(413,ERRORS[413])
                yield chunk
        await call('PUT',dav(s,path),s,content=chunks(),headers={'If-None-Match':'*','Content-Type':'application/octet-stream'})
        return {'ok':True}

    @app.get(API+'/download')
    async def download(request: Request, path: str, preview: bool=False):
        s = session(request)
        path = clean_path(path,False)
        req = app.state.client.build_request('GET',dav(s,path))
        try: r = await app.state.client.send(req,auth=s.auth,stream=True)
        except httpx.HTTPError: raise HTTPException(502,'Không tải được tệp. Hãy thử lại.')
        if r.status_code >= 400:
            await r.aclose()
            raise HTTPException(r.status_code if r.status_code in ERRORS else 502,ERRORS.get(r.status_code,'Không tải được tệp.'))
        mime = r.headers.get('content-type','application/octet-stream').split(';')[0].strip().lower()
        if preview:
            raster = mime in {'image/png','image/jpeg','image/webp','image/gif'}
            text = mime == 'text/plain' or path.lower().endswith(('.txt','.md','.csv','.log','.json'))
            if not raster and not text:
                await r.aclose(); raise HTTPException(415,'Định dạng này chưa hỗ trợ xem trước. Hãy tải tệp xuống.')
            limit = 20*1024**2 if raster else 2*1024**2
            content = bytearray()
            try:
                async for chunk in r.aiter_bytes():
                    content.extend(chunk)
                    if len(content)>limit: raise HTTPException(413,'Tệp quá lớn để xem trước. Hãy tải xuống.')
            finally: await r.aclose()
            return Response(bytes(content),media_type=mime if raster else 'text/plain')
        filename = quote(path.rsplit('/',1)[-1],safe='')
        return StreamingResponse(r.aiter_bytes(),media_type='application/octet-stream',
            headers={'Content-Disposition':f"attachment; filename=download; filename*=UTF-8''{filename}"},background=BackgroundTask(r.aclose))

    @app.get(API+'/shares')
    async def shares(request: Request, path: str):
        s = session(request)
        path = clean_path(path,False)
        data = await ocs('/ocs/v2.php/apps/files_sharing/api/v1/shares',s,params={'path':'/'+path})
        return {'items':[{'id':x['id'],'label':x.get('share_with_displayname') or ('Liên kết công khai' if int(x['share_type'])==3 else 'Chia sẻ'),'url':x.get('url') if int(x['share_type'])==3 else None} for x in (data or [])]}

    if static_dir.is_dir(): app.mount('/static/files',StaticFiles(directory=static_dir),name='files-static')
    @app.get('/{path:path}',response_class=HTMLResponse)
    async def index(path: str):
        if path.startswith(('api/','static/')): raise HTTPException(404)
        try:
            manifest = json.loads((static_dir/'.vite/manifest.json').read_text())
            entry = manifest['src/legacy/files/main.tsx']
            css = ''.join(f'<link rel="stylesheet" href="/static/files/{x}">' for x in entry.get('css',[]))
            return f'<!doctype html><html lang="vi"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="color-scheme" content="light dark"><title>CloudBox Files · Kho tệp</title>{css}</head><body><div id="root"></div><script type="module" src="/static/files/{entry["file"]}"></script></body></html>'
        except (FileNotFoundError,KeyError): raise HTTPException(503,'Giao diện chưa được build.')
    return app

app = create_app(upstream=os.environ.get('NEXTCLOUD_UPSTREAM','http://nextcloud'),public=os.environ.get('NEXTCLOUD_PUBLIC','http://localhost:8080'))
