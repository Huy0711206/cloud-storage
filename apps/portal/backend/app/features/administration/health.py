"""Read-only dependency checks for CloudBox readiness and operations."""
import json
import os
import shutil

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.features.storage.capacity import MIN_FREE_BYTES, pool_usage
from app.features.storage.native_service import storage_root


def database_status(db: Session) -> str:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        db.rollback()
        return "unavailable"
    return "ok"


def storage_status() -> dict:
    try:
        root = storage_root()
        if not root.is_dir() or not os.access(root, os.R_OK | os.W_OK | os.X_OK):
            return {"status": "unavailable"}
        usage = shutil.disk_usage(root)
    except OSError:
        return {"status": "unavailable"}

    if usage.free <= MIN_FREE_BYTES:
        status = "critical"
    elif usage.free <= max(2 * MIN_FREE_BYTES, usage.total // 10):
        status = "low"
    else:
        status = "ok"
    return {"status": status, "total_bytes": usage.total, "free_bytes": usage.free}


def dependency_status(db: Session) -> dict:
    return {"database": database_status(db), "storage": storage_status()}


def is_ready(checks: dict) -> bool:
    return checks["database"] == "ok" and checks["storage"]["status"] != "unavailable"


def diagnostics(db: Session) -> dict:
    checks = dependency_status(db)
    capacity = None
    if checks["database"] == "ok":
        try:
            capacity = pool_usage(db)
        except (SQLAlchemyError, ValueError):
            db.rollback()
    if capacity is None:
        checks["budget"] = {"status": "unavailable"}
        return checks

    available = capacity["available_bytes"]
    limit = capacity["pool_limit_bytes"]
    if available is None:
        status = "unlimited"
    elif available == 0:
        status = "full"
    elif available * 5 <= limit:
        status = "low"
    else:
        status = "ok"
    checks["budget"] = {"status": status, **capacity}
    return checks


if __name__ == "__main__":
    with SessionLocal() as session:
        report = diagnostics(session)
    print(json.dumps(report, ensure_ascii=True))
    raise SystemExit(0 if is_ready(report) else 1)
