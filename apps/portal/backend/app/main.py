import logging
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from .core import models  # noqa: F401  (đăng ký bảng)
from .core import bootstrap
from .features.billing import service as services
from .core.config import settings
from .core.database import Base, SessionLocal, engine
from .shared.http import Redirect, render
from .features.administration import routes as admin
from .features.authentication import routes as auth
from .features.accounts import routes as accounts
from .features.accounts import dashboard
from .features.public import routes as public
from .features.billing import routes as billing
from .features.payments import routes as payments
from .features.storage import routes as files, version_routes, collaboration_routes, team_version_routes
from .features.billing import benefit_routes
from .features.storage import native_models, migration_models  # noqa: F401

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("portal")

MAINTENANCE_INTERVAL = 3600  # giây


def _maintenance_loop() -> None:
    while True:
        try:
            with SessionLocal() as db:
                n = services.run_maintenance(db)
                from .features.authentication.otp import purge_expired
                from .features.storage.native_service import owner_lock, expire_uploads, collect_garbage
                from .features.storage.native_models import UploadSession
                purge_expired(db)
                collect_garbage(db)
                owners = [row[0] for row in db.query(UploadSession.owner_id).filter_by(state="pending").distinct()]
                for owner in owners:
                    with owner_lock(db, owner):
                        expire_uploads(db, owner)
                        db.commit()
                if n:
                    log.info("Đã hạ %d tài khoản hết hạn về gói Miễn phí", n)
        except Exception:
            log.exception("Lỗi khi chạy bảo trì định kỳ")
        time.sleep(MAINTENANCE_INTERVAL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        from .core.models import User
        from .features.storage.migration_models import MigrationRecord
        if db.query(User).filter(User.nc_username.is_not(None)).first() and not db.get(MigrationRecord, "manifest"):
            raise RuntimeError("Native storage migration is required before serving existing accounts")
        bootstrap.seed(db)
    threading.Thread(target=_maintenance_loop, daemon=True, name="maintenance").start()
    yield


app = FastAPI(title="CloudBox Portal", lifespan=lifespan)

app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")

@app.middleware("http")
async def browser_security(request: Request, call_next):
    from urllib.parse import parse_qs
    from .shared.csrf import origin_allowed, token_matches
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        if request.headers.get("origin") == "null":
            supplied=request.headers.get("x-csrf-token", "")
            if not supplied and request.headers.get("content-type", "").split(";", 1)[0] == "application/x-www-form-urlencoded":
                try:length=int(request.headers.get("content-length", "0"))
                except ValueError:length=0
                if 0 < length <= 65536:
                    body=await request.body()  # CachedRequest replays these bytes to FastAPI forms.
                    if len(body) <= 65536:
                        try:supplied=parse_qs(body.decode("utf-8"),max_num_fields=50).get("csrf_token",[""])[0]
                        except (ValueError,UnicodeError):pass
            request.state.csrf_validated=token_matches(request,supplied)
        if not origin_allowed(request,settings.base_url):
            return JSONResponse({"detail":"Phiên biểu mẫu không hợp lệ. Hãy mở lại trang CloudBox rồi thử lại."},status_code=403)
    response = await call_next(request)
    if not request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "private, no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    same_site="lax",
    https_only=settings.base_url.startswith("https://"),
    max_age=7 * 24 * 3600,
)

app.include_router(public.router)
app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(dashboard.router)
app.include_router(billing.router)
app.include_router(payments.router)
app.include_router(admin.router)
app.include_router(files.router)
app.include_router(version_routes.router)
app.include_router(collaboration_routes.router)
app.include_router(team_version_routes.router)
app.include_router(benefit_routes.router)


@app.exception_handler(Redirect)
async def _redirect_handler(request: Request, exc: Redirect):
    return RedirectResponse(exc.url, status_code=303)


@app.exception_handler(StarletteHTTPException)
async def _http_error_handler(request: Request, exc: StarletteHTTPException):
    titles = {403: "Không có quyền", 404: "Không tìm thấy trang"}
    return render(request, "message.html", status_code=exc.status_code,
                  title=titles.get(exc.status_code, "Có lỗi xảy ra"), text=str(exc.detail), kind="error")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
