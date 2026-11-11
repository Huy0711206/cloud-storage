"""One-shot migration rehearsal: disposable SQLite and blobs in tmpfs only."""
import json
import os
from pathlib import Path
from sqlalchemy import create_engine, text
from app.core.database import Base, engine
from app.core.models import Plan, User, Order
from . import native_models, migration_models
from .migrate import migrate, verify

def main():
    if engine.url.get_backend_name() != 'sqlite' or not str(engine.url.database).startswith('/tmp/'):
        raise RuntimeError('Rehearsal requires a disposable SQLite database under /tmp')
    Base.metadata.create_all(engine)
    source=create_engine(os.environ['ORIGINAL_DATABASE_URL'])
    with source.connect() as c,engine.begin() as dest:
        c.execute(text('SET TRANSACTION READ ONLY'))
        for model in (Plan,User,Order):
            rows=[dict(r._mapping) for r in c.execute(text(f'select * from {model.__tablename__} order by id'))]
            if rows:dest.execute(model.__table__.insert(),rows)
    with engine.connect() as c:
        admin=c.execute(text("select id from users where role='admin' order by id limit 1")).scalar_one()
    dry=migrate(Path('/legacy/data'),admin,dry_run=True)
    actual=migrate(Path('/legacy/data'),admin)
    verified=verify()
    repeated=migrate(Path('/legacy/data'),admin)
    assert actual['files']==repeated['files'] and actual['bytes']==repeated['bytes']
    with engine.connect() as c:
        count=c.execute(text('select count(*) from storage_nodes where not is_folder')).scalar_one()
        assert count==actual['files']
    print(json.dumps({'dry':dry,'import':actual,'verify':verified,'idempotent':True}))

if __name__=='__main__':main()
