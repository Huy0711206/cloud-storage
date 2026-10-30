"""CloudBox Mail UI and a narrowly scoped same-origin Mailpit API gateway.

This process owns no inbox, SMTP listener, database or CloudBox application secret.
Mailpit remains the sole source of mail data; only explicit message IDs may mutate.
"""
from contextlib import asynccontextmanager
from http.cookiejar import CookieJar
import html
import json
import os
from pathlib import Path, PurePosixPath
import re
from urllib.parse import urlsplit

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

DEFAULT_STATIC_DIR = Path(__file__).parent / "static" / "mail"
DEFAULT_UPSTREAM = "http://mailpit:8025"
ID = re.compile(r"[A-Za-z0-9_-]{1,128}\Z")
PART = re.compile(r"[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*\Z")
MESSAGE = re.compile(r"message/([A-Za-z0-9_-]{1,128})(?:/(headers|raw|part/([A-Za-z0-9_.-]{1,128})))?\Z")
MAX_BODY = 65536


class NoCookieJar(CookieJar):
    """The shared API client must never retain per-request upstream state."""
    def extract_cookies(self, response, request):
        return

    def set_cookie(self, cookie):
        return


def _origin(value: str) -> str:
    parsed = urlsplit(value)
    if (parsed.scheme not in {"http", "https"} or not parsed.netloc
            or parsed.username or parsed.password or parsed.path not in {"", "/"}
            or parsed.query or parsed.fragment):
        raise ValueError("UPSTREAM_URL must be a fixed server-owned HTTP origin")
    return value.rstrip("/")


def frontend_assets(directory: Path) -> dict:
    manifest = json.loads((directory / ".vite" / "manifest.json").read_text(encoding="utf-8"))
    entry = manifest["src/mail/main.tsx"]
    files = [entry["file"], *entry.get("css", [])]
    for name in files:
        path = PurePosixPath(name)
        if not name or path.is_absolute() or ".." in path.parts or "\\" in name:
            raise ValueError("Invalid frontend asset path")
        if not (directory / name).is_file():
            raise ValueError("Missing frontend asset")
    return {"js": "/static/mail/" + entry["file"], "css": ["/static/mail/" + name for name in entry.get("css", [])]}


def _query(request: Request, path: str) -> dict:
    allowed = {"start", "limit"} if path == "messages" else {"query", "start", "limit", "tz"} if path == "search" else {"dl"} if path.endswith("/raw") else set()
    result = {}
    for key, value in request.query_params.multi_items():
        if key not in allowed or key in result:
            raise ValueError("Tham số không được hỗ trợ.")
        if key == "start" and (not value.isdecimal() or int(value) > 10000000):
            raise ValueError("Vị trí trang không hợp lệ.")
        if key == "limit" and (not value.isdecimal() or not 1 <= int(value) <= 200):
            raise ValueError("Số thư mỗi trang phải từ 1 đến 200.")
        if key == "query" and (not value.strip() or len(value) > 2000):
            raise ValueError("Nội dung tìm kiếm không hợp lệ.")
        if key == "tz" and (len(value) > 100 or not re.fullmatch(r"[A-Za-z0-9_+./-]+", value)):
            raise ValueError("Múi giờ không hợp lệ.")
        if key == "dl" and value != "1":
            raise ValueError("Tham số tải thư không hợp lệ.")
        result[key] = value
    if path == "search" and "query" not in result:
        raise ValueError("Nhập nội dung cần tìm.")
    return result


def _same_origin(request: Request) -> bool:
    if request.headers.get("sec-fetch-site") == "cross-site":
        return False
    origin = request.headers.get("origin")
    if not origin:
        return True
    parsed = urlsplit(origin)
    return parsed.scheme == request.url.scheme and parsed.netloc.lower() == request.url.netloc.lower()


def create_app(*, upstream_url: str = DEFAULT_UPSTREAM, static_dir: Path = DEFAULT_STATIC_DIR,
               transport: httpx.AsyncBaseTransport | None = None) -> FastAPI:
    upstream_url = _origin(upstream_url)
    static_dir = Path(static_dir)

    @asynccontextmanager
    async def lifespan(app):
        frontend_assets(static_dir)
        async with httpx.AsyncClient(transport=transport, follow_redirects=False, cookies=NoCookieJar(),
                                     timeout=httpx.Timeout(20, connect=4), trust_env=False) as client:
            app.state.upstream = client
            yield

    app = FastAPI(title="CloudBox Mail", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "[::1]", "testserver"])

    @app.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers["x-content-type-options"] = "nosniff"
        response.headers["referrer-policy"] = "no-referrer"
        response.headers["x-frame-options"] = "DENY"
        response.headers["cache-control"] = "no-store"
        if response.headers.get("content-type", "").startswith("text/html"):
            response.headers["content-security-policy"] = (
                "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; "
                "frame-src 'self' blob:; object-src 'none'; base-uri 'none'; "
                "form-action 'none'; frame-ancestors 'none'"
            )
        return response

    app.mount("/static/mail", StaticFiles(directory=str(static_dir), check_dir=False), name="mail-assets")

    @app.get("/healthz")
    async def health():
        try:
            frontend_assets(static_dir)
            response = await app.state.upstream.get(upstream_url + "/api/v1/messages", params={"limit": "1"})
            response.raise_for_status()
            if not isinstance(response.json().get("messages"), list):
                raise ValueError("Mailpit did not return a message list")
            return {"status": "ok", "variant": "mail-preview"}
        except (httpx.HTTPError, OSError, ValueError, KeyError, TypeError, AttributeError):
            return JSONResponse({"status": "unavailable", "variant": "mail-preview"}, status_code=503)

    @app.get("/")
    async def index():
        try:
            assets = frontend_assets(static_dir)
        except (OSError, ValueError, KeyError, TypeError):
            return HTMLResponse("<h1>Chưa tải được CloudBox Mail</h1><p>Hãy build lại giao diện thư.</p>", status_code=503)
        css = "".join('<link rel="stylesheet" href="' + html.escape(url, quote=True) + '">' for url in assets["css"])
        return HTMLResponse('<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light dark"><title>Hộp thư thử nghiệm · CloudBox</title>' + css + '</head><body><div id="root"></div><script type="module" src="' + html.escape(assets["js"], quote=True) + '"></script></body></html>')

    @app.api_route("/api/v1/{path:path}", methods=["GET", "PUT", "DELETE", "POST", "PATCH", "HEAD", "OPTIONS"])
    async def proxy(request: Request, path: str):
        match = MESSAGE.fullmatch(path)
        allowed_path = path in {"messages", "search"} or bool(match)
        if not allowed_path or (match and match.group(3) and not PART.fullmatch(match.group(3))):
            return JSONResponse({"detail": "Chức năng API không được hỗ trợ."}, status_code=404)
        allowed_method = request.method == "GET" or (path == "messages" and request.method in {"PUT", "DELETE"})
        if not allowed_method:
            return JSONResponse({"detail": "Thao tác không được hỗ trợ."}, status_code=405)
        if not _same_origin(request):
            return JSONResponse({"detail": "Yêu cầu phải đến từ giao diện hộp thư."}, status_code=403)
        try:
            query = _query(request, path)
        except ValueError as error:
            return JSONResponse({"detail": str(error)}, status_code=422)
        data = None
        if request.method in {"PUT", "DELETE"}:
            if query:
                return JSONResponse({"detail": "Chỉ thay đổi các thư đã chọn."}, status_code=422)
            raw = await request.body()
            if len(raw) > MAX_BODY:
                return JSONResponse({"detail": "Yêu cầu quá lớn."}, status_code=413)
            try:
                data = json.loads(raw)
            except (ValueError, UnicodeError):
                return JSONResponse({"detail": "Nội dung yêu cầu không hợp lệ."}, status_code=422)
            keys = {"IDs", "Read"} if request.method == "PUT" else {"IDs"}
            if (not isinstance(data, dict) or set(data) != keys or not isinstance(data.get("IDs"), list)
                    or not 1 <= len(data["IDs"]) <= 100
                    or any(not isinstance(value, str) or not ID.fullmatch(value) for value in data["IDs"])
                    or (request.method == "PUT" and not isinstance(data.get("Read"), bool))):
                return JSONResponse({"detail": "Chọn từ 1 đến 100 thư trước khi thực hiện."}, status_code=422)
        try:
            upstream_response = await app.state.upstream.request(request.method, upstream_url + "/api/v1/" + path,
                                                                  params=query, json=data,
                                                                  headers={"accept-encoding": "identity"})
        except httpx.RequestError:
            return JSONResponse({"detail": "Chưa kết nối được Mailpit. Hãy thử lại."}, status_code=503)
        if upstream_response.is_redirect:
            return JSONResponse({"detail": "Mailpit trả về chuyển hướng không được hỗ trợ."}, status_code=502)
        upstream_type = upstream_response.headers.get("content-type", "")
        media_type = "application/json" if "application/json" in upstream_type else "text/plain; charset=utf-8"
        disposition = None
        if match and match.group(3) and upstream_response.is_success:
            # Downloads never execute as HTML/SVG/XML on our application's origin.
            media_type = "application/octet-stream"
            original = upstream_response.headers.get("content-disposition", "")
            filename = original.split(";", 1)[1].strip() if ";" in original else 'filename="attachment"'
            disposition = "attachment; " + filename.replace("\r", "").replace("\n", "")
        elif match and match.group(2) == "raw":
            media_type = "text/plain; charset=utf-8"
            if query.get("dl") == "1" and upstream_response.is_success:
                disposition = f'attachment; filename="{match.group(1)}.eml"'
        response = Response(content=upstream_response.content, status_code=upstream_response.status_code,
                            headers={"content-type": media_type})
        if disposition:
            response.headers["content-disposition"] = disposition
        return response

    return app


app = create_app(upstream_url=os.environ.get("UPSTREAM_URL", DEFAULT_UPSTREAM))
