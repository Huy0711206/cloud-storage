"""Team-scoped revision access; never delegates through personal API endpoints."""
from fastapi import APIRouter,Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.models import User
from .routes import StorageRoute,storage_user,same_origin
from .native_service import blob_path
from .version_service import list_versions,lookup_version,restore_version

router=APIRouter(route_class=StorageRoute,dependencies=[Depends(same_origin)])


@router.get('/api/teams/{team_id}/files/{node_id}/versions')
def versions(team_id:str,node_id:str,db:Session=Depends(get_db),user:User=Depends(storage_user)):
    return list_versions(db,user,node_id,team_id=team_id)


@router.get('/api/teams/{team_id}/files/{node_id}/versions/{version_id}/download')
def download(team_id:str,node_id:str,version_id:str,db:Session=Depends(get_db),user:User=Depends(storage_user)):
    version=lookup_version(db,user,node_id,version_id,team_id=team_id)
    return FileResponse(blob_path(version.blob_key),filename=version.name,media_type='application/octet-stream',
                        headers={'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'})


@router.post('/api/teams/{team_id}/files/{node_id}/versions/{version_id}/restore')
def restore(team_id:str,node_id:str,version_id:str,db:Session=Depends(get_db),user:User=Depends(storage_user)):
    return restore_version(db,user,node_id,version_id,team_id=team_id)
