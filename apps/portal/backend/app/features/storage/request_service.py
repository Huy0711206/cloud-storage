"""Token-scoped upload-only requests: no public list/read endpoint exists."""
from datetime import timedelta
import hashlib,secrets
from app.core.config import settings
from app.core.models import utcnow
from app.features.billing.entitlements import require_feature
from . import native_service as s
from .native_models import UploadSession
from .collaboration_models import FileRequest,RequestUpload
from .access import assert_personal_node, fresh_user

MAX_FILE=2*1024**3
MAX_TOTAL=10*1024**3


def request_usage(db,request):
    rows=db.query(UploadSession).join(RequestUpload,RequestUpload.upload_id==UploadSession.id).filter(RequestUpload.request_id==request.id).all()
    done=[u for u in rows if u.state=='complete']
    pending=[u for u in rows if u.state=='pending' and u.expires_at>utcnow()]
    return {'used_bytes':sum(u.size for u in done),'reserved_bytes':sum(u.size for u in pending),'upload_count':len(done)}


def serialize_request(db,row):
    return {'id':row.id,'title':row.title,'parent_id':row.parent_id,'expires_at':row.expires_at.isoformat()+'Z',
            'closed':bool(row.closed_at),'max_file_size':row.max_file_size,'max_total_size':row.max_total_size,
            **request_usage(db,row)}


def list_requests(db,user):
    user=fresh_user(db,user.id)
    return {'items':[serialize_request(db,row) for row in db.query(FileRequest).filter_by(owner_id=user.id).order_by(FileRequest.created_at.desc()).limit(200)]}


def create_request(db,user,title,parent_id,expires_days,max_file_size,max_total_size):
    with s.owner_guard(db,user.id):
        user=fresh_user(db,user.id)
        require_feature(user,'file_requests')
        title=s.valid_name(title)
        if len(title)>120:raise s.StorageError(400,'Tiêu đề tối đa 120 ký tự.')
        if not parent_id:raise s.StorageError(400,'Hãy chọn thư mục nhận tệp cụ thể.')
        assert_personal_node(db,user.id,parent_id)
        s.parent_folder(db,user.id,parent_id)
        if not 1<=expires_days<=30 or not 1<=max_file_size<=MAX_FILE or not max_file_size<=max_total_size<=MAX_TOTAL:
            raise s.StorageError(400,'Hạn dùng 1–30 ngày, mỗi tệp tối đa 2 GB và tổng tối đa 10 GB.')
        if db.query(FileRequest).filter(FileRequest.owner_id==user.id,FileRequest.closed_at.is_(None),FileRequest.expires_at>utcnow()).count()>=20:
            raise s.StorageError(429,'Tối đa 20 yêu cầu nhận tệp đang mở.')
        token=secrets.token_urlsafe(32)
        row=FileRequest(owner_id=user.id,parent_id=parent_id,title=title,token_hash=hashlib.sha256(token.encode()).hexdigest(),expires_at=utcnow()+timedelta(days=expires_days),max_file_size=max_file_size,max_total_size=max_total_size)
        db.add(row);db.commit()
        return {**serialize_request(db,row),'url':settings.base_url+'/r/'+token}


def close_request(db,user,request_id):
    with s.owner_guard(db,user.id):
        row=db.query(FileRequest).filter_by(id=request_id,owner_id=user.id).first()
        if not row:raise s.StorageError(404,'Không tìm thấy yêu cầu nhận tệp.')
        row.closed_at=utcnow();db.commit();return {'ok':True}


from .access import request_access as public_request


def start_public_upload(db,token,name,size):
    return s.start_upload(db,None,name,None,size,request_token=token)


def request_upload_action(db,token,upload_id,action,data=None,offset=None):
    if action=='abort':return s.abort_upload(db,None,upload_id,request_token=token)
    if action=='chunk':return s.append_chunk(db,None,upload_id,data,offset,request_token=token)
    result=s.finish_upload(db,None,upload_id,request_token=token)
    # An upload-only capability never returns receiver node IDs or download URLs.
    return {'ok':True,'name':result['name'],'size':result['size']}
