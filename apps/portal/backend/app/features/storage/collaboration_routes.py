"""Same-origin group operations and upload-only file request routes."""
from html import escape
import json,secrets
from fastapi import APIRouter,Depends,Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel,Field,StrictInt
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.models import User
from app.shared.csrf import ensure_token
from .routes import StorageRoute,storage_user,same_origin,download_node
from . import native_service as s,team_service as teams,request_service as requests

router=APIRouter(route_class=StorageRoute,dependencies=[Depends(same_origin)])

class NameBody(BaseModel):
    name:str=Field(min_length=1,max_length=120)
class MemberBody(BaseModel):
    email:str=Field(min_length=3,max_length=255)
    role:str='viewer'
class RoleBody(BaseModel):
    role:str
class FolderBody(BaseModel):
    name:str=Field(min_length=1,max_length=255)
    parent_id:str|None=None
class ChangeBody(BaseModel):
    name:str|None=Field(default=None,min_length=1,max_length=255)
    parent_id:str|None=None
class UploadBody(FolderBody):
    replace_node_id:str|None=Field(default=None,max_length=32)
    size:StrictInt=Field(ge=0,le=2**63-1)
class RequestBody(BaseModel):
    title:str=Field(min_length=1,max_length=120)
    parent_id:str=Field(min_length=1,max_length=32)
    expires_days:StrictInt=Field(default=7,ge=1,le=30)
    max_file_size:StrictInt=Field(default=1024**3,ge=1,le=requests.MAX_FILE)
    max_total_size:StrictInt=Field(default=5*1024**3,ge=1,le=requests.MAX_TOTAL)
class PublicUploadBody(BaseModel):
    name:str=Field(min_length=1,max_length=255)
    size:StrictInt=Field(ge=0,le=requests.MAX_FILE)

@router.get('/api/teams')
def list_teams(db:Session=Depends(get_db),user:User=Depends(storage_user)):return teams.list_teams(db,user)
@router.post('/api/teams',status_code=201)
def create_team(body:NameBody,db:Session=Depends(get_db),user:User=Depends(storage_user)):return teams.create_team(db,user,body.name)
@router.post('/api/team-invitations/{invitation_id}/accept')
def accept_invitation(invitation_id:str,db:Session=Depends(get_db),user:User=Depends(storage_user)):return teams.accept_invitation(db,user,invitation_id)
@router.get('/api/teams/{team_id}/members')
def members(team_id:str,db:Session=Depends(get_db),user:User=Depends(storage_user)):return teams.members(db,user,team_id)
@router.post('/api/teams/{team_id}/members',status_code=201)
def invite(team_id:str,body:MemberBody,db:Session=Depends(get_db),user:User=Depends(storage_user)):return teams.invite(db,user,team_id,body.email,body.role)
@router.patch('/api/teams/{team_id}/members/{user_id}')
def member_role(team_id:str,user_id:int,body:RoleBody,db:Session=Depends(get_db),user:User=Depends(storage_user)):return teams.change_member(db,user,team_id,user_id,body.role)
@router.delete('/api/teams/{team_id}/members/{user_id}')
def remove_member(team_id:str,user_id:int,db:Session=Depends(get_db),user:User=Depends(storage_user)):return teams.change_member(db,user,team_id,user_id,remove=True)
@router.get('/api/teams/{team_id}/files')
def files(team_id:str,parent:str|None=None,q:str='',trash:bool=False,offset:int=0,limit:int=200,db:Session=Depends(get_db),user:User=Depends(storage_user)):return teams.team_files(db,user,team_id,parent,q[:255],trash,offset,limit)
@router.post('/api/teams/{team_id}/folders',status_code=201)
def folder(team_id:str,body:FolderBody,db:Session=Depends(get_db),user:User=Depends(storage_user)):return teams.team_folder(db,user,team_id,body.name,body.parent_id)
@router.patch('/api/teams/{team_id}/files/{node_id}')
def change(team_id:str,node_id:str,body:ChangeBody,db:Session=Depends(get_db),user:User=Depends(storage_user)):
    changes=body.model_dump(exclude_unset=True)
    if 'name' in changes and changes['name'] is None:raise s.StorageError(400,'Tên không hợp lệ.')
    return teams.team_change(db,user,team_id,node_id,changes)
@router.post('/api/teams/{team_id}/files/{node_id}/trash')
def trash(team_id:str,node_id:str,db:Session=Depends(get_db),user:User=Depends(storage_user)):return teams.team_trash(db,user,team_id,node_id)
@router.post('/api/teams/{team_id}/files/{node_id}/restore')
def restore(team_id:str,node_id:str,db:Session=Depends(get_db),user:User=Depends(storage_user)):return teams.team_trash(db,user,team_id,node_id,True)
@router.get('/api/teams/{team_id}/files/{node_id}/download')
def download(team_id:str,node_id:str,db:Session=Depends(get_db),user:User=Depends(storage_user)):
    team,_,_=teams.access(db,user,team_id)
    return download_node(teams.scoped_node(db,team,node_id))
@router.post('/api/teams/{team_id}/uploads',status_code=201)
def upload(team_id:str,body:UploadBody,db:Session=Depends(get_db),user:User=Depends(storage_user)):return teams.team_upload(db,user,team_id,body.name,body.parent_id,body.size,body.replace_node_id)

async def chunk_data(request):
    try:offset=int(request.headers['upload-offset'])
    except (KeyError,ValueError):raise s.StorageError(400,'Thiếu Upload-Offset hợp lệ.')
    data=bytearray()
    async for block in request.stream():
        if len(data)+len(block)>s.CHUNK_SIZE:raise s.StorageError(413,'Mỗi phần tải lên tối đa 8 MB.')
        data.extend(block)
    return bytes(data),offset

@router.put('/api/teams/{team_id}/uploads/{upload_id}')
async def chunk(team_id:str,upload_id:str,request:Request,db:Session=Depends(get_db),user:User=Depends(storage_user)):
    data,offset=await chunk_data(request)
    return teams.team_upload_action(db,user,team_id,upload_id,'chunk',data,offset)
@router.post('/api/teams/{team_id}/uploads/{upload_id}/complete')
def complete(team_id:str,upload_id:str,db:Session=Depends(get_db),user:User=Depends(storage_user)):return teams.team_upload_action(db,user,team_id,upload_id,'complete')
@router.delete('/api/teams/{team_id}/uploads/{upload_id}')
def abort(team_id:str,upload_id:str,db:Session=Depends(get_db),user:User=Depends(storage_user)):return teams.team_upload_action(db,user,team_id,upload_id,'abort')

@router.get('/api/file-requests')
def list_requests(db:Session=Depends(get_db),user:User=Depends(storage_user)):return requests.list_requests(db,user)
@router.post('/api/file-requests',status_code=201)
def create_request(body:RequestBody,db:Session=Depends(get_db),user:User=Depends(storage_user)):return requests.create_request(db,user,**body.model_dump())
@router.delete('/api/file-requests/{request_id}')
def close_request(request_id:str,db:Session=Depends(get_db),user:User=Depends(storage_user)):return requests.close_request(db,user,request_id)
@router.post('/api/requests/{token}/uploads',status_code=201)
def request_upload(token:str,body:PublicUploadBody,db:Session=Depends(get_db)):return requests.start_public_upload(db,token,body.name,body.size)
@router.put('/api/requests/{token}/uploads/{upload_id}')
async def request_chunk(token:str,upload_id:str,request:Request,db:Session=Depends(get_db)):
    requests.public_request(db,token)
    data,offset=await chunk_data(request)
    return requests.request_upload_action(db,token,upload_id,'chunk',data,offset)
@router.post('/api/requests/{token}/uploads/{upload_id}/complete')
def request_complete(token:str,upload_id:str,db:Session=Depends(get_db)):return requests.request_upload_action(db,token,upload_id,'complete')
@router.delete('/api/requests/{token}/uploads/{upload_id}')
def request_abort(token:str,upload_id:str,db:Session=Depends(get_db)):return requests.request_upload_action(db,token,upload_id,'abort')

@router.get('/r/{token}',response_class=HTMLResponse)
def request_page(token:str,request:Request,db:Session=Depends(get_db)):
    row,_=requests.public_request(db,token)
    csrf=ensure_token(request);nonce=secrets.token_urlsafe(20)
    # All untrusted text goes through HTML escaping or textContent, never executable HTML.
    prefix='/api/requests/'+token+'/uploads'
    script="""
const input=document.querySelector('#files'),button=document.querySelector('#send'),status=document.querySelector('#status');
async function call(url,method,body,extra={}){let r=await fetch(url,{method,body,credentials:'same-origin',headers:{'X-CSRF-Token':CSRF,...extra}});let j=await r.json();if(!r.ok)throw Error(j.detail||'Chưa thể gửi tệp.');return j}
button.addEventListener('click',async()=>{button.disabled=true;let current=null;try{if(!input.files.length)throw Error('Hãy chọn tệp để gửi.');for(let file of input.files){status.textContent='Đang gửi '+file.name;let u=await call(PREFIX,'POST',JSON.stringify({name:file.name,size:file.size}),{'Content-Type':'application/json'});current=u.id;for(let offset=0;offset<file.size;offset+=u.chunk_size){await call(PREFIX+'/'+u.id,'PUT',file.slice(offset,offset+u.chunk_size),{'Upload-Offset':String(offset)})}await call(PREFIX+'/'+u.id+'/complete','POST');current=null;}status.textContent='Đã gửi thành công. Người nhận đã có tệp của bạn.';input.value=''}catch(e){if(current)await call(PREFIX+'/'+current,'DELETE').catch(()=>{});status.textContent=e.message}finally{button.disabled=false}});
"""
    html='''<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Gửi tệp · CloudBox</title><style>body{font:16px system-ui;margin:0;background:#f8fafc;color:#181b22}main{max-width:680px;margin:40px auto;padding:28px;background:white;border:1px solid #dbe0e8;border-radius:16px}button,input{font:inherit;padding:12px;max-width:100%;box-sizing:border-box}button{background:#074ce0;color:white;border:0;border-radius:8px;cursor:pointer}button:disabled{opacity:.5}p{line-height:1.6}a{color:#074ce0}</style></head><body><main><a href="/">CloudBox.</a><h1>'''+escape(row.title)+'''</h1><p>Bạn chỉ có thể gửi tệp. Bạn không có quyền xem hoặc tải dữ liệu trong kho của người nhận.</p><p>Mỗi tệp tối đa '''+str(round(row.max_file_size/1024**2))+''' MB. Liên kết hết hạn '''+escape(row.expires_at.isoformat()+'Z')+'''.</p><label for="files">Chọn tệp cần gửi</label><p><input id="files" type="file" multiple></p><button id="send" type="button">Gửi tệp</button><p id="status" role="status" aria-live="polite"></p><p>Không gửi thông tin nhạy cảm nếu bạn chưa xác nhận người nhận.</p></main><script nonce="'''+nonce+'">const PREFIX='+json.dumps(prefix)+',CSRF='+json.dumps(csrf)+';'+script+'</script></body></html>'
    return HTMLResponse(html,headers={'Cache-Control':'no-store','Referrer-Policy':'no-referrer','Content-Security-Policy':f"default-src 'none'; style-src 'unsafe-inline'; script-src 'nonce-{nonce}'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'"})
