from datetime import timedelta
from pathlib import Path

from fastapi import Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.models import User

BASE_DIR = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
templates.env.policies["json.dumps_kwargs"] = {"ensure_ascii": False, "sort_keys": True}


class Redirect(Exception):
    def __init__(self, url: str):
        self.url = url


# ---- bộ lọc hiển thị trong template ----
def vnd(n) -> str:
    return f"{int(n):,}".replace(",", ".") + " ₫"


def quota(gb) -> str:
    gb = int(gb)
    return f"{gb // 1024} TB" if gb >= 1024 and gb % 1024 == 0 else f"{gb} GB"


def human_bytes(n) -> str:
    n = float(n or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.2f} {unit}"
        n /= 1024


def dt(value) -> str:
    return (value + timedelta(hours=7)).strftime("%d/%m/%Y %H:%M") if value else "—"


templates.env.filters.update(vnd=vnd, quota=quota, human_bytes=human_bytes, dt=dt)


# ---- phiên đăng nhập ----
def flash(request: Request, message: str, kind: str = "info") -> None:
    request.session.setdefault("flash", []).append([kind, message])


def render(request: Request, name: str, user: User | None = None, status_code: int = 200, **ctx):
    from .frontend import assets, payload
    from .csrf import ensure_token
    ctx["csrf_token"] = ensure_token(request)
    flashes = request.session.pop("flash", [])
    ui_assets = assets()
    if ui_assets:
        page = payload(name, user, ctx, flashes, settings.nc_public_url)
        return templates.TemplateResponse(request, "app.html", {"page": page, "ui_assets": ui_assets}, status_code=status_code)
    ctx.update(user=user, flashes=flashes, settings=settings)
    return templates.TemplateResponse(request, name, ctx, status_code=status_code)


def current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    uid = request.session.get("uid")
    if not uid:
        return None
    user = db.get(User, uid)
    if not user or not user.is_active:
        request.session.clear()
        return None
    return user


def require_user(user: User | None = Depends(current_user)) -> User:
    if not user:
        raise Redirect("/login")
    return user


def require_admin(user: User = Depends(require_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập trang này.")
    return user
