"""Approved restoration to 5/100/500/2048 GiB plan quotas; shared trial pool remains 20 GiB. Never deletes or rewrites user data."""
import hashlib,json
from sqlalchemy import select
from app.core.database import SessionLocal
from app.core.models import User,Plan,Order
from app.features.storage.native_models import FileNode
from app.features.storage.migration_models import FileVersion
TARGET={"free":5,"basic":100,"standard":500,"premium":2048}
EXPECTED_PRICE={"free":0,"basic":39000,"standard":89000,"premium":199000}

def digest(db,model):
    rows=[dict(row) for row in db.execute(select(model.__table__).order_by(*model.__table__.primary_key.columns)).mappings()]
    return {"count":len(rows),"sha256":hashlib.sha256(json.dumps(rows,sort_keys=True,default=str,ensure_ascii=False).encode()).hexdigest()}

with SessionLocal() as db:
    before={model.__tablename__:digest(db,model) for model in (User,Order,FileNode,FileVersion)}
    plans=db.query(Plan).filter(Plan.code.in_(TARGET)).with_for_update().all()
    assert len(plans)==4,"Expected exactly four known plan codes"
    unchanged={p.id:(p.code,p.name,p.price_vnd,p.is_active,p.sort) for p in plans}
    old={p.code:p.quota_gb for p in plans}
    for p in plans:
        assert p.price_vnd==EXPECTED_PRICE[p.code],"Price changed; stop rather than overwrite"
        p.quota_gb=TARGET[p.code]
    db.flush()
    assert all((p.code,p.name,p.price_vnd,p.is_active,p.sort)==unchanged[p.id] for p in plans)
    after={model.__tablename__:digest(db,model) for model in (User,Order,FileNode,FileVersion)}
    assert before==after,"Unexpected modification; transaction not committed"
    db.commit()
    print(json.dumps({"old_quota_gb":old,"new_quota_gb":TARGET,"preserved":after},ensure_ascii=False))
