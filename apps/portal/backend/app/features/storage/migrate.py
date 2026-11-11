"""Offline, checksum-verified import from read-only Nextcloud disk/database.

Run only with Nextcloud in maintenance mode and the old Portal stopped.
--dry-run inventories without writes; --verify checks the imported blob manifest.
No account or billing fields are changed. The source volume is never modified.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import mimetypes
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import uuid

from sqlalchemy import create_engine, text
from app.core.database import Base, SessionLocal, engine
from app.core.models import User
from .native_models import FileNode
from .migration_models import FileVersion, MigrationRecord
from .native_service import blob_path, lock_owner, valid_name, StorageError


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def fingerprint():
    """Proof of unchanged identities and commerce, including credential hashes."""
    h=hashlib.sha256()
    with engine.connect() as c:
        for table in ('users','plans','orders'):
            for row in c.execute(text(f'select * from {table} order by id')):
                h.update(json.dumps(list(row),default=str,ensure_ascii=False).encode())
    return h.hexdigest()


def safe(root, relative):
    rel=PurePosixPath(relative)
    if rel.is_absolute() or '..' in rel.parts:raise RuntimeError('Unsafe source path')
    path=root.joinpath(*rel.parts)
    if not path.resolve().is_relative_to(root.resolve()):raise RuntimeError('Source escaped root')
    # Resolve() alone would conceal symlinks within the volume.
    cursor=path
    while cursor!=root:
        if cursor.is_symlink():raise RuntimeError('Symlink requires explicit migration review')
        cursor=cursor.parent
    return path


def source_entries(home, relative):
    """Inventory every directory entry before type tests; dangling links must fail closed."""
    root=safe(home,relative)
    if not root.exists():return []
    if not root.is_dir():raise RuntimeError('Expected source directory is not a directory')
    result=[]
    for p in sorted(root.rglob('*')):
        safe(home,p.relative_to(home).as_posix())
        if not p.is_dir() and not p.is_file():raise RuntimeError('Non-regular source file requires explicit migration review')
        result.append(p)
    return result


def validate_display_name(name):
    try:normalized=valid_name(name)
    except StorageError as exc:raise RuntimeError('Source filename needs explicit migration review') from exc
    if normalized!=name:raise RuntimeError('Source filename normalization would rename existing data; cutover blocked')


def validate_source_root(root):
    if not root.is_absolute():raise RuntimeError('Source root must be absolute')
    if root.is_symlink() or not root.is_dir():raise RuntimeError('Missing or linked source data root')
    for cursor in root.parents:
        if cursor.is_symlink():raise RuntimeError('Source data root traverses a symlink')
    markers=[safe(root,name) for name in ('.ocdata','.ncdata')]
    if not any(marker.is_file() for marker in markers):raise RuntimeError('Nextcloud data marker missing; incorrect source root')


def validate_live_inventory(home,index):
    cached={path:row for path,row in index.items() if path=='files' or path.startswith('files/')}
    files=safe(home,'files')
    if not files.exists():
        if cached:raise RuntimeError('Mapped source home/files missing although filecache contains content')
        return []
    entries=source_entries(home,'files')
    actual={p.relative_to(home).as_posix():p for p in entries}
    for relative,row in cached.items():
        if relative=='files':continue
        p=actual.get(relative)
        if p is None:raise RuntimeError('Filecache entry has no corresponding source path; cutover blocked')
        if p.is_file() and row.get('size') is not None and int(row['size'])>=0 and p.stat().st_size!=int(row['size']):raise RuntimeError('Source bytes disagree with cached file size; cutover blocked')
    if any(relative not in cached for relative in actual):raise RuntimeError('Unindexed source path requires filecache reconciliation; cutover blocked')
    return entries


def stable(value):return uuid.uuid5(uuid.NAMESPACE_URL,'cloudbox-native:'+value).hex


def copy_blob(source,key):
    checksum=sha(source)
    target=blob_path(key)
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():
        if sha(target)!=checksum:raise RuntimeError('Existing destination differs; nothing overwritten')
    else:
        temp=target.with_suffix('.importing')
        try:
            # A stale .importing file is temporary destination state, never the retained source.
            with source.open('rb') as src,temp.open('wb') as dst:
                shutil.copyfileobj(src,dst,1024*1024)
                dst.flush();os.fsync(dst.fileno())
            if sha(temp)!=checksum:raise RuntimeError('Checksum mismatch before import')
            # Atomic fail-if-exists publication on the persistent destination filesystem.
            # Unlike replace(), this cannot overwrite a destination created concurrently.
            try:os.link(temp,target)
            except FileExistsError:
                if sha(target)!=checksum:raise RuntimeError('Destination appeared with different bytes; no overwrite allowed')
        finally:
            temp.unlink(missing_ok=True)
    if sha(target)!=checksum or sha(source)!=checksum:raise RuntimeError('Checksum/source changed during import')
    return checksum


def load_source():
    url=os.environ.get('SOURCE_DATABASE_URL')
    src=create_engine(url if url else engine.url.set(database='nextcloud'))
    with src.connect() as c:
        c.execute(text('SET TRANSACTION READ ONLY'))
        tables=set(c.execute(text("select tablename from pg_tables where schemaname='public'")).scalars())
        prefix=next(t[:-len('filecache')] for t in tables if t.endswith('_filecache'))
        if not re.fullmatch(r'[a-zA-Z0-9_]+',prefix):raise RuntimeError('Invalid source prefix')
        def rows(name):
            return [dict(r._mapping) for r in c.execute(text(f'select * from {prefix}{name}'))] if prefix+name in tables else []
        source={k:rows(k) for k in ('storages','filecache','share','files_trash','files_versions','share_external','mounts')}
    if source['share'] or source['share_external']:raise RuntimeError('Existing shares need a reviewed permission/token migration before cutover')
    if any(r.get('encrypted') for r in source['filecache']):raise RuntimeError('Encrypted source requires explicit key-aware migration')
    if any('LocalHomeMountProvider' not in (r.get('mount_provider_class') or '') for r in source['mounts']):raise RuntimeError('External storage mount requires explicit migration')
    return source


def migrate(source_root,admin_owner,dry_run=False):
    validate_source_root(source_root)
    source=load_source()
    before=fingerprint()
    report={'dry_run':dry_run,'files':0,'folders':0,'bytes':0,'versions':0,'version_bytes':0,'trash_roots':0,'trash_versions':0,'sha256_verified':0,'unmapped_homes':0,'history_rows':len(source['files_versions']),'source_untouched':True}
    if not dry_run:Base.metadata.create_all(engine)
    with SessionLocal() as db:
        users={u.nc_username:u for u in db.query(User).all() if u.nc_username}
        nc_admin=os.environ.get('NEXTCLOUD_ADMIN_USER','')
        if admin_owner:
            admin=db.get(User,admin_owner)
            if not admin or admin.role!='admin':raise RuntimeError('Admin mapping must name an existing Portal admin ID')
            if not nc_admin:raise RuntimeError('NEXTCLOUD_ADMIN_USER required to map the source admin')
            users[nc_admin]=admin
        file_index={r['fileid']:r for r in source['filecache']}
        known_homes={store['id'][6:] for store in source['storages'] if store['id'].startswith('home::')}
        for candidate in source_root.iterdir():
            if candidate.name in known_homes:continue
            if candidate.is_symlink():raise RuntimeError('Unexpected symlink in source data root')
            if candidate.is_dir() and any((candidate/name).exists() for name in ('files','files_versions','files_trashbin')):
                raise RuntimeError('Data home not present in source storage index; cutover blocked')
        for store in source['storages']:
            if not store['id'].startswith('home::'):continue
            uid=store['id'][6:]
            home=safe(source_root,uid)
            user=users.get(uid)
            if not user:
                cached_content=any(r['storage']==store['numeric_id'] and r['path'].startswith('files/') for r in source['filecache'])
                if cached_content or (home.is_dir() and any(p.is_file() or p.is_symlink() for p in home.rglob('*'))):
                    report['unmapped_homes']+=1
                continue
            if not dry_run:lock_owner(db,user.id)
            node_map={}
            index={r['path']:r for r in source['filecache'] if r['storage']==store['numeric_id']}
            validate_live_inventory(home,index)

            def import_node(path,rel,parent=None,deleted=None,trash_root=None,display_name=None):
                safe(home,path.relative_to(home).as_posix())
                if not path.is_dir() and not path.is_file():raise RuntimeError('Non-regular source path')
                source_key=f'{store["numeric_id"]}:{rel}'
                nid=stable(source_key)
                is_dir=path.is_dir()
                name=display_name or path.name
                validate_display_name(name)
                cached=index.get(rel,{})
                mtime=datetime.fromtimestamp(path.stat().st_mtime,timezone.utc).replace(tzinfo=None)
                size=0 if is_dir else path.stat().st_size
                report['folders' if is_dir else 'files']+=1
                report['bytes']+=size
                node_map[rel]=nid
                if not dry_run:
                    digest=None if is_dir else copy_blob(path,nid)
                    if not is_dir:report['sha256_verified']+=1
                    n=db.get(FileNode,nid)
                    expected_trash=trash_root or (nid if deleted else None)
                    if n and (n.owner_id!=user.id or n.sha256!=digest or n.size!=size or n.parent_id!=parent or n.name!=name or n.is_folder!=is_dir or n.deleted_at!=deleted or n.trash_root_id!=expected_trash):raise RuntimeError('Destination metadata differs; no overwrite allowed')
                    if not n:
                        n=FileNode(id=nid,owner_id=user.id,parent_id=parent,name=name,is_folder=is_dir,size=size,
                                   blob_key=None if is_dir else nid,sha256=digest,mime_type=mimetypes.guess_type(path.name)[0] or 'application/octet-stream',
                                   modified_at=mtime,deleted_at=deleted,trash_root_id=trash_root or (nid if deleted else None),
                                   legacy_file_id=str(cached.get('fileid') or ''),legacy_storage=store['id'])
                        db.add(n);db.flush()
                if is_dir:
                    for child in sorted(path.iterdir()):
                        safe(home,str(child.relative_to(home).as_posix()))
                        import_node(child,rel+'/'+child.name,nid,deleted,trash_root or (nid if deleted else None))
                return nid

            files=home/'files'
            if files.is_dir():
                for p in sorted(files.iterdir()):
                    safe(home,p.relative_to(home).as_posix())
                    import_node(p,'files/'+p.name)
            trash_entries=source_entries(home,'files_trashbin/files')
            indexed_trash={row['id']+'.d'+str(row['timestamp']) for row in source['files_trash'] if row['user']==uid}
            if any(p.relative_to(home/'files_trashbin/files').parts[0] not in indexed_trash for p in trash_entries):raise RuntimeError('Unindexed trash bytes require explicit migration review')
            for row in source['files_trash']:
                if row['user']!=uid:continue
                rel='files_trashbin/files/'+row['id']+'.d'+str(row['timestamp'])
                p=safe(home,rel)
                if not p.exists():raise RuntimeError('Trash record source bytes missing')
                original=PurePosixPath(row.get('location') or '')
                parent=node_map.get('files/'+str(original).strip('/'))
                tid=import_node(p,rel,parent,datetime.fromtimestamp(int(row['timestamp']),timezone.utc).replace(tzinfo=None),display_name=PurePosixPath(row['id']).name)
                if not dry_run:
                    key='trash:'+str(row['auto_id'])
                    if not db.get(MigrationRecord,key):db.add(MigrationRecord(key=key,payload=json.dumps(row,default=str)))
                report['trash_roots']+=1
            versions=safe(home,'files_versions')
            if versions.is_dir():
                for p in source_entries(home,'files_versions'):
                    if p.is_dir():continue
                    safe(home,p.relative_to(home).as_posix())
                    rel=p.relative_to(versions).as_posix()
                    match=re.fullmatch(r'(.+)\.v(\d+)',rel)
                    if not match:raise RuntimeError('Unrecognized version filename')
                    key=f'version:{store["numeric_id"]}:{rel}'
                    vid=stable(key)
                    size=p.stat().st_size
                    report['versions']+=1;report['version_bytes']+=size
                    if not dry_run:
                        digest=copy_blob(p,vid);report['sha256_verified']+=1
                        old=db.query(FileVersion).filter_by(source_key=key).first()
                        if old and (old.sha256!=digest or old.owner_id!=user.id or old.size!=size or old.blob_key!=vid or old.node_id!=node_map.get('files/'+match[1])):raise RuntimeError('Existing version differs')
                        if not old:db.add(FileVersion(id=vid,owner_id=user.id,node_id=node_map.get('files/'+match[1]),source_key=key,name=PurePosixPath(match[1]).name,size=size,blob_key=vid,sha256=digest,
                                                   created_at=datetime.fromtimestamp(int(match[2]),timezone.utc).replace(tzinfo=None)))
            # Deleted-file versions may have a different filename grammar. Preserve bytes and
            # ownership with explicit source provenance rather than guessing their current node.
            for p in source_entries(home,'files_trashbin/versions'):
                if p.is_dir():continue
                rel=p.relative_to(home/'files_trashbin/versions').as_posix()
                key=f'trash-version:{store["numeric_id"]}:{rel}'
                vid=stable(key);size=p.stat().st_size
                report['versions']+=1;report['trash_versions']+=1;report['version_bytes']+=size
                if not dry_run:
                    digest=copy_blob(p,vid);report['sha256_verified']+=1
                    old=db.query(FileVersion).filter_by(source_key=key).first()
                    if old and (old.sha256!=digest or old.owner_id!=user.id or old.size!=size):raise RuntimeError('Existing trash version differs')
                    if not old:db.add(FileVersion(id=vid,owner_id=user.id,node_id=None,source_key=key,name=p.name,size=size,blob_key=vid,sha256=digest,created_at=datetime.fromtimestamp(p.stat().st_mtime,timezone.utc).replace(tzinfo=None)))
            if not dry_run:db.commit()
        if report['unmapped_homes']:raise RuntimeError('Source homes without an approved Portal owner remain; cutover blocked')
        if not dry_run:
            # Preserve all historical rows, including metadata whose old blob no longer exists.
            for row in source['files_versions']:
                key='history:'+str(row['id'])
                if not db.get(MigrationRecord,key):db.add(MigrationRecord(key=key,payload=json.dumps(row,default=str)))
            db.commit()
    after=fingerprint()
    if before!=after:raise RuntimeError('Identity or commerce changed during migration; cutover blocked')
    report.update(identity_commerce_unchanged=True,identity_commerce_digest=after)
    if not dry_run:
        with SessionLocal() as db:
            row=db.get(MigrationRecord,'manifest')
            if not row:db.add(MigrationRecord(key='manifest',payload=json.dumps(report)))
            else:row.payload=json.dumps(report)
            db.commit()
    return report


def verify():
    report={'files_verified':0,'versions_verified':0,'bytes_verified':0}
    with SessionLocal() as db:
        for model,kind in [(FileNode,'files_verified'),(FileVersion,'versions_verified')]:
            for n in db.query(model).filter(model.blob_key.is_not(None)):
                p=blob_path(n.blob_key)
                if not p.is_file() or p.stat().st_size!=n.size or sha(p)!=n.sha256:raise RuntimeError('Stored blob verification failed')
                report[kind]+=1;report['bytes_verified']+=n.size
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',default='/legacy/data')
    parser.add_argument('--admin-owner',type=int)
    parser.add_argument('--dry-run',action='store_true')
    parser.add_argument('--verify',action='store_true')
    args=parser.parse_args()
    result=verify() if args.verify else migrate(Path(args.source_root),args.admin_owner,args.dry_run)
    print(json.dumps(result,ensure_ascii=False))
