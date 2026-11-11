"""Same-origin authenticated native storage API and read-only public shares."""
from html import escape
import errno
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.routing import APIRoute
from pydantic import BaseModel, Field, StrictInt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.models import User
from app.shared.http import current_user
from . import native_service as s
from .native_models import FileNode
from .access import personal_node, team_node_ids
from . import share_service as sharing


class StorageRoute(APIRoute):
    def get_route_handler(self):
        handler=super().get_route_handler()
        async def wrapped(request:Request):
            try:return await handler(request)
            except s.StorageError as exc:return JSONResponse({"detail":exc.detail},status_code=exc.status,headers={"Cache-Control":"no-store"})
            except HTTPException as exc:return JSONResponse({"detail":exc.detail},status_code=exc.status)
            except OSError as exc:
                detail="Máy chủ không còn đủ dung lượng đĩa. Hãy liên hệ quản trị viên." if exc.errno==errno.ENOSPC else "Kho tệp tạm thời không khả dụng. Hãy thử lại hoặc liên hệ quản trị viên."
                return JSONResponse({"detail":detail},status_code=507 if exc.errno==errno.ENOSPC else 503)
        return wrapped


def same_origin(request:Request):
    if request.method in ("GET","HEAD","OPTIONS"):return
    from app.shared.csrf import origin_allowed
    if not origin_allowed(request,settings.base_url):raise s.StorageError(403,"Phiên thao tác không hợp lệ. Hãy mở lại CloudBox.")


def storage_user(user:User|None=Depends(current_user)):
    if not user:raise s.StorageError(401,"Vui lòng đăng nhập.")
    if not user.is_verified:raise s.StorageError(403,"Vui lòng xác minh tài khoản trước khi mở kho tệp.")
    return user


router=APIRouter(route_class=StorageRoute,dependencies=[Depends(same_origin)])


class FolderBody(BaseModel):
    name:str=Field(min_length=1,max_length=255)
    parent_id:str|None=None


class UpdateBody(BaseModel):
    name:str|None=Field(default=None,min_length=1,max_length=255)
    parent_id:str|None=None


class UploadBody(FolderBody):
    replace_node_id:str|None=None
    size:StrictInt=Field(ge=0,le=2**63-1)


class ShareBody(BaseModel):
    expires_at:str|None=Field(default=None,max_length=64)
    password:str|None=Field(default=None,max_length=128)


class PurgeBody(BaseModel):
    confirm_id:str=Field(min_length=1,max_length=32)


@router.get("/api/files")
def files(parent:str|None=None,q:str="",trash:bool=False,sort:str="name",offset:int=0,limit:int=200,db:Session=Depends(get_db),user:User=Depends(storage_user)):
    return s.list_nodes(db,user,parent or None,q[:255],trash,sort,offset,limit)


@router.get("/api/storage/usage")
def usage(db:Session=Depends(get_db),user:User=Depends(storage_user)):
    return s.quota_usage(db,user)


@router.get("/api/shares")
def my_shares(db:Session=Depends(get_db),user:User=Depends(storage_user)):
    return s.all_shares(db,user)


@router.post("/api/files/folders",status_code=201)
def folder(body:FolderBody,db:Session=Depends(get_db),user:User=Depends(storage_user)):
    return s.create_folder(db,user,body.name,body.parent_id)


@router.get("/api/files/{node_id}")
def detail(node_id:str,db:Session=Depends(get_db),user:User=Depends(storage_user)):
    return s.serialize_node(personal_node(db,user,node_id))


@router.patch("/api/files/{node_id}")
def change(node_id:str,body:UpdateBody,db:Session=Depends(get_db),user:User=Depends(storage_user)):
    changes=body.model_dump(exclude_unset=True)
    if "name" in changes and changes["name"] is None:raise s.StorageError(400,"Tên không hợp lệ.")
    return s.update_node(db,user,node_id,changes)


@router.post("/api/files/{node_id}/trash")
def trash(node_id:str,db:Session=Depends(get_db),user:User=Depends(storage_user)):
    return s.trash_node(db,user,node_id)


@router.post("/api/files/{node_id}/restore")
def restore(node_id:str,db:Session=Depends(get_db),user:User=Depends(storage_user)):
    return s.restore_node(db,user,node_id)


@router.delete("/api/files/{node_id}")
def purge(node_id:str,body:PurgeBody,db:Session=Depends(get_db),user:User=Depends(storage_user)):
    return s.purge_node(db,user,node_id,body.confirm_id)


def download_node(node:FileNode):
    if node.is_folder:raise s.StorageError(400,"Hãy mở thư mục để tải từng tệp.")
    p=s.blob_path(node.blob_key)
    if not p.is_file():raise s.StorageError(503,"Tệp tạm thời không khả dụng. Hãy liên hệ quản trị viên.")
    return FileResponse(p,filename=node.name,media_type="application/octet-stream",headers={"Cache-Control":"private, no-store","X-Content-Type-Options":"nosniff","Content-Security-Policy":"default-src 'none'"})


@router.get("/api/files/{node_id}/download")
def download(node_id:str,db:Session=Depends(get_db),user:User=Depends(storage_user)):
    return download_node(personal_node(db,user,node_id))


@router.post("/api/uploads",status_code=201)
def upload_init(body:UploadBody,db:Session=Depends(get_db),user:User=Depends(storage_user)):
    return s.start_upload(db,user,body.name,body.parent_id,body.size,body.replace_node_id)


@router.put("/api/uploads/{upload_id}")
async def upload_chunk(upload_id:str,request:Request,db:Session=Depends(get_db),user:User=Depends(storage_user)):
    try:offset=int(request.headers["upload-offset"])
    except (KeyError,ValueError):raise s.StorageError(400,"Thiếu Upload-Offset hợp lệ.")
    blocks=bytearray()
    async for block in request.stream():
        if len(blocks)+len(block)>s.CHUNK_SIZE:raise s.StorageError(413,"Mỗi phần tải lên tối đa 8 MB.")
        blocks.extend(block)
    return s.append_chunk(db,user,upload_id,bytes(blocks),offset)


@router.post("/api/uploads/{upload_id}/complete")
def complete(upload_id:str,db:Session=Depends(get_db),user:User=Depends(storage_user)):
    return s.finish_upload(db,user,upload_id)


@router.delete("/api/uploads/{upload_id}")
def abort(upload_id:str,db:Session=Depends(get_db),user:User=Depends(storage_user)):
    return s.abort_upload(db,user,upload_id)


@router.get("/api/files/{node_id}/shares")
def shares(node_id:str,db:Session=Depends(get_db),user:User=Depends(storage_user)):
    return {"items":s.list_shares(db,user,node_id)}


@router.post("/api/files/{node_id}/shares",status_code=201)
def share(node_id:str,body:ShareBody|None=None,db:Session=Depends(get_db),user:User=Depends(storage_user)):
    body=body or ShareBody()
    return s.create_share(db,user,node_id,body.expires_at,body.password)


@router.delete("/api/shares/{share_id}")
def unshare(share_id:str,db:Session=Depends(get_db),user:User=Depends(storage_user)):
    return s.revoke_share(db,user,share_id)


@router.get("/s/{token}",response_class=HTMLResponse)
def public_share(token:str,request:Request,folder:str|None=None,offset:int=0,db:Session=Depends(get_db)):
    try:
        share=sharing.authorize(db,token,request.scope.get("session",{}))
        root=s.owned_node(db,share.owner_id,share.node_id)
    except s.StorageError as exc:
        if exc.status==401:return password_form(request,token)
        raise
    node=s.shared_node(db,root,folder) if folder else root
    prefix="/s/"+quote(token,safe="")
    links=[]
    if node.is_folder:
        if node.id!=root.id:
            links.append(f'<li><a href="{prefix}?folder={quote(node.parent_id or root.id,safe="")}">← Thư mục trước</a></li>')
        query=db.query(FileNode).filter_by(owner_id=node.owner_id,parent_id=node.id,deleted_at=None).order_by(FileNode.is_folder.desc(),FileNode.name,FileNode.id)
        offset=max(0,offset)
        hidden=team_node_ids(db,node.owner_id)
        if hidden:query=query.filter(FileNode.id.notin_(hidden))
        children=query.populate_existing().offset(offset).limit(201).all()
        if offset:
            links.append(f'<li><a href="{prefix}?folder={node.id}&amp;offset={max(0,offset-200)}">← Trang trước</a></li>')
        if len(children)>200:
            links.append(f'<li><a href="{prefix}?folder={node.id}&amp;offset={offset+200}">Trang tiếp →</a></li>')
            children=children[:200]
    else:children=[node]
    for child in children:
        url=f'{prefix}?folder={child.id}' if child.is_folder else f'{prefix}/download/{child.id}'
        links.append(f'<li><a href="{url}">{"📁 " if child.is_folder else "↓ "}{escape(child.name)}</a></li>')
    sharing.record(db,share.id,"view")
    html='''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Chia sẻ tệp · CloudBox</title><style>body{font:16px system-ui;background:#f8fafc;color:#181b22;margin:0}main{max-width:760px;margin:48px auto;padding:32px;background:white;border:1px solid #dbe0e8;border-radius:16px}a{color:#074ce0;text-decoration:none}li{padding:14px;border-bottom:1px solid #edf0f5}ul{list-style:none;padding:0}p{color:#526070}</style><main><a href="/">CloudBox.</a><h1>'''+escape(node.name)+'''</h1><p>Liên kết chỉ xem và tải xuống. Quyền sở hữu tệp được giữ nguyên.</p><ul>'''+("".join(links) or "<li>Thư mục trống.</li>")+'''</ul></main></html>'''
    return HTMLResponse(html,headers={"Cache-Control":"no-store","Referrer-Policy":"no-referrer","X-Content-Type-Options":"nosniff","Content-Security-Policy":"default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'"})


@router.get("/s/{token}/download/{node_id}")
def public_download(token:str,node_id:str,request:Request,db:Session=Depends(get_db)):
    share=sharing.authorize(db,token,request.scope.get("session",{}))
    response=download_node(s.shared_node(db,s.owned_node(db,share.owner_id,share.node_id),node_id))
    sharing.record(db,share.id,"download")
    return response


def password_form(request,token,error="",status=200):
    from app.shared.csrf import ensure_token
    csrf=ensure_token(request)
    html='<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Mật khẩu chia sẻ · CloudBox</title><style>body{font:16px system-ui;background:#f8fafc;color:#181b22}main{max-width:440px;margin:48px auto;padding:28px;background:white;border:1px solid #dbe0e8;border-radius:16px}input,button{box-sizing:border-box;min-height:44px;padding:10px;width:100%;margin-top:12px}button{background:#074ce0;color:white;border:0;border-radius:8px}a{color:#074ce0}</style><main><a href="/">CloudBox.</a><h1>Mở liên kết được bảo vệ</h1><p>Nhập mật khẩu do người chia sẻ cung cấp. Quyền truy cập có hiệu lực trong một giờ trên trình duyệt này.</p>'
    html+=f'<p role="alert">{escape(error)}</p>' if error else ""
    html+=f'<form method="post" action="/s/{quote(token,safe="")}/unlock"><input type="hidden" name="csrf_token" value="{escape(csrf,quote=True)}"><label for="share-password">Mật khẩu liên kết</label><input id="share-password" name="password" type="password" maxlength="128" required autocomplete="current-password"><button type="submit">Mở liên kết</button></form></main></html>'
    return HTMLResponse(html,status_code=status,headers={"Cache-Control":"no-store","Referrer-Policy":"no-referrer","Content-Security-Policy":"default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'"})


@router.post("/s/{token}/unlock")
def unlock_share(token:str,request:Request,password:str=Form(max_length=128),db:Session=Depends(get_db)):
    try:sharing.unlock(db,token,password,request.session,request.client.host if request.client else "unknown")
    except s.StorageError as exc:
        if exc.status in (401,429):return password_form(request,token,exc.detail,exc.status)
        raise
    return RedirectResponse("/s/"+quote(token,safe=""),status_code=303)

