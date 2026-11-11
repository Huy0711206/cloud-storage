"""Owner-only access to retained historical file contents."""
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.models import User
from .routes import StorageRoute, storage_user, same_origin
from .native_service import blob_path, StorageError
from .migration_models import FileVersion
from .version_models import ReplacementUpload, VersionPolicy  # register additive tables
from .version_service import lookup_version, restore_version, list_versions

router=APIRouter(route_class=StorageRoute, dependencies=[Depends(same_origin)])

@router.get('/api/files/{node_id}/versions')
def versions(node_id:str,db:Session=Depends(get_db),user:User=Depends(storage_user)):
    return list_versions(db,user,node_id)

@router.get('/api/files/{node_id}/versions/{version_id}/download')
def download_version(node_id:str,version_id:str,db:Session=Depends(get_db),user:User=Depends(storage_user)):
    v=lookup_version(db,user,node_id,version_id)
    p=blob_path(v.blob_key)
    if not p.is_file():raise StorageError(503,'Phiên bản tạm thời không khả dụng.')
    return FileResponse(p,filename=v.name,media_type='application/octet-stream',headers={'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'})

@router.post('/api/files/{node_id}/versions/{version_id}/restore')
def restore(node_id:str,version_id:str,db:Session=Depends(get_db),user:User=Depends(storage_user)):
    return restore_version(db,user,node_id,version_id)
