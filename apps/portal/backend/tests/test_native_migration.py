"""Migration fail-closed checks against a temporary source tree and isolated DB."""
from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.core.models import Plan,User
from app.features.storage import migrate
from app.features.storage.native_models import FileNode
from app.features.storage.migration_models import FileVersion


@pytest.fixture
def source(tmp_path,monkeypatch):
    root=tmp_path/'nextcloud-data';root.mkdir();(root/'.ocdata').touch()
    home=root/'source@gmail.com';(home/'files').mkdir(parents=True)
    (home/'files'/'document.txt').write_bytes(b'original')
    monkeypatch.setenv('STORAGE_ROOT',str(tmp_path/'native'))
    engine=create_engine('sqlite:///'+str(tmp_path/'migration.db'))
    factory=sessionmaker(engine,expire_on_commit=False,autoflush=False)
    Base.metadata.create_all(engine)
    with factory() as db:
        p=Plan(code='original',name='Original',quota_gb=100,price_vnd=39000,sort=0)
        db.add(p);db.flush()
        db.add(User(id=1,email='source@gmail.com',nc_username='source@gmail.com',full_name='Original identity',password_hash='original-hash',is_verified=True,plan_id=p.id));db.commit()
    data={'storages':[{'id':'home::source@gmail.com','numeric_id':1}],
          'filecache':[{'fileid':1,'storage':1,'path':'files','size':8},{'fileid':2,'storage':1,'path':'files/document.txt','size':8}],
          'share':[],'share_external':[],'mounts':[],'files_trash':[],'files_versions':[]}
    monkeypatch.setattr(migrate,'engine',engine)
    monkeypatch.setattr(migrate,'SessionLocal',factory)
    monkeypatch.setattr(migrate,'load_source',lambda:data)
    yield root,home,data,factory
    engine.dispose()


def test_wrong_root_and_marker_block_before_import(source,tmp_path):
    root,_,_,factory=source
    wrong=tmp_path/'wrong';wrong.mkdir()
    with pytest.raises(RuntimeError,match='marker'):migrate.migrate(wrong,None)
    with pytest.raises(RuntimeError,match='Missing'):migrate.migrate(tmp_path/'missing',None)
    with factory() as db:assert db.query(FileNode).count()==0


def test_missing_home_or_cached_file_blocks_cutover(source):
    root,home,_,factory=source
    (home/'files'/'document.txt').unlink()
    with pytest.raises(RuntimeError,match='corresponding'):migrate.migrate(root,None)
    (home/'files').rmdir()
    with pytest.raises(RuntimeError,match='home/files missing'):migrate.migrate(root,None)
    with factory() as db:assert db.query(FileNode).count()==0


def test_uncached_disk_bytes_and_orphan_trash_are_not_silently_skipped(source):
    root,home,_,_=source
    (home/'files'/'unindexed.bin').write_bytes(b'unindexed')
    with pytest.raises(RuntimeError,match='Unindexed source'):migrate.migrate(root,None,True)
    (home/'files'/'unindexed.bin').unlink()
    trash=home/'files_trashbin'/'files';trash.mkdir(parents=True)
    (trash/'orphan.d123').write_bytes(b'orphan')
    with pytest.raises(RuntimeError,match='Unindexed trash'):migrate.migrate(root,None,True)


def test_dry_run_then_idempotent_checksum_import_preserves_identity(source):
    root,home,_,factory=source
    before=migrate.fingerprint()
    dry=migrate.migrate(root,None,True)
    assert dry['files']==1 and dry['sha256_verified']==0
    with factory() as db:assert db.query(FileNode).count()==0
    first=migrate.migrate(root,None)
    second=migrate.migrate(root,None)
    assert first['files']==second['files']==1 and first['sha256_verified']==1
    assert before==migrate.fingerprint()
    assert migrate.verify()['bytes_verified']==8
    assert (home/'files'/'document.txt').read_bytes()==b'original'
    with factory() as db:assert db.query(FileNode).count()==1


def test_retry_refuses_changed_destination_tree(source):
    root,_,_,factory=source
    migrate.migrate(root,None)
    with factory() as db:db.query(FileNode).first().name='changed-by-user.txt';db.commit()
    with pytest.raises(RuntimeError,match='metadata differs'):migrate.migrate(root,None)


def test_trash_original_name_and_deleted_versions_are_retained(source):
    root,home,data,factory=source
    trash=home/'files_trashbin'/'files';trash.mkdir(parents=True)
    (trash/'deleted.txt.d123').write_bytes(b'deleted')
    data['files_trash']=[{'user':'source@gmail.com','id':'deleted.txt','timestamp':'123','location':'','auto_id':99}]
    versions=home/'files_trashbin'/'versions';versions.mkdir()
    (versions/'deleted.txt.v100.d123').write_bytes(b'historical')
    report=migrate.migrate(root,None)
    assert report['trash_roots']==1 and report['trash_versions']==1
    migrate.migrate(root,None)
    with factory() as db:
        deleted=db.query(FileNode).filter(FileNode.deleted_at.is_not(None)).one()
        assert deleted.name=='deleted.txt' and deleted.trash_root_id==deleted.id
        version=db.query(FileVersion).one()
        assert version.owner_id==1 and version.size==10 and version.node_id is None
    assert migrate.verify()['versions_verified']==1


def test_symlink_even_when_dangling_version_directory_blocks(source,tmp_path):
    root,home,_,_=source
    version=home/'files_versions';version.mkdir()
    link=version/'dangling'
    try:link.symlink_to(tmp_path/'does-not-exist',target_is_directory=True)
    except OSError:pytest.skip('Host cannot create test symlinks')
    with pytest.raises(RuntimeError,match='Symlink|Source escaped root'):migrate.migrate(root,None,True)


def test_copy_never_overwrites_different_destination(source):
    _,home,_,_=source
    original=home/'files'/'document.txt'
    key='a'*32
    destination=migrate.blob_path(key);destination.parent.mkdir(parents=True);destination.write_bytes(b'different')
    with pytest.raises(RuntimeError,match='differs'):migrate.copy_blob(original,key)
    assert destination.read_bytes()==b'different' and original.read_bytes()==b'original'
