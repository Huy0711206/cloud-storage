import logging
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from .core import models  # noqa: F401  (đăng ký bảng)
from .core import bootstrap
from .features.billing import service as services
from .core.config import settings
from .core.database import Base, SessionLocal, engine
from .shared.http import Redirect, current_user, render
from .features.administration import routes as admin
from .features.authentication import routes as auth
from .features.accounts import routes as accounts
from .features.accounts import dashboard
from .features.public import routes as public
from .features.billing import routes as billing
from .features.payments import routes as payments

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("portal")

MAINTENANCE_INTERVAL = 3600  # giây


def _maintenance_loop() -> None:
    while True:
        try:
            with SessionLocal() as db:
                n = services.run_maintenance(db)
                if n:
                    log.info("Đã hạ %d tài khoản hết hạn về gói Miễn phí", n)
        except Exception:
            log.exception("Lỗi khi chạy bảo trì định kỳ")
        time.sleep(MAINTENANCE_INTERVAL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        bootstrap.seed(db)
    threading.Thread(target=_maintenance_loop, daemon=True, name="maintenance").start()
    yield


app = FastAPI(title="CloudBox Portal", lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    same_site="lax",
    https_only=settings.base_url.startswith("https://"),
    max_age=7 * 24 * 3600,
)
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")

app.include_router(public.router)
app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(dashboard.router)
app.include_router(billing.router)
app.include_router(payments.router)
app.include_router(admin.router)


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
