"""Serve a design preview while all application behavior stays on the stable portal.

This gateway owns no database, application secret, account, or maintenance job.
It forwards only to its configured upstream and replaces only CloudBox UI asset tags.
"""
from contextlib import asynccontextmanager
from http.cookiejar import CookieJar
import html
import json
import os
from pathlib import Path, PurePosixPath
import re
from urllib.parse import urlsplit, urlunsplit

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

DEFAULT_STATIC_DIR = Path(__file__).parent / "static" / "ui"
UPSTREAM = "http://portal:8000"
PUBLIC_ORIGIN = "http://localhost:8001"
HOP_HEADERS = {
    b"connection", b"keep-alive", b"proxy-authenticate", b"proxy-authorization",
    b"te", b"trailer", b"transfer-encoding", b"upgrade",
}
REQUEST_REMOVED = HOP_HEADERS | {
    b"host", b"content-length", b"accept-encoding", b"forwarded",
    b"x-forwarded-for", b"x-forwarded-host", b"x-forwarded-proto",
}
RESPONSE_REMOVED = HOP_HEADERS | {b"content-length", b"content-encoding"}
UI_STYLESHEET = re.compile(
    r"""<link\b(?=[^>]*\brel\s*=\s*["']stylesheet["'])(?=[^>]*\bhref\s*=\s*["']/static/ui/)[^>]*>""",
    re.IGNORECASE,
)
UI_MODULE = re.compile(
    r"""<script\b(?=[^>]*\btype\s*=\s*["']module["'])(?=[^>]*\bsrc\s*=\s*["']/static/ui/)[^>]*>\s*</script\s*>""",
    re.IGNORECASE,
)


class NoCookieJar(CookieJar):
    """Never retain upstream cookies between visitors; explicit Cookie passes through."""

    def extract_cookies(self, response, request):
        return

    def set_cookie(self, cookie):
        return


def _removed_headers(raw_headers, base):
    removed = set(base)
    for key, value in raw_headers:
        if key.lower() == b"connection":
            removed.update(part.strip().lower() for part in value.split(b",") if part.strip())
    return removed


def frontend_assets(directory: Path):
    manifest = json.loads((directory / ".vite" / "manifest.json").read_text(encoding="utf-8"))
    entry = manifest["src/main.tsx"]
    files = [entry["file"], *entry.get("css", [])]
    for name in files:
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or "\\" in name:
            raise ValueError("Invalid frontend asset path")
        if not (directory / name).is_file():
            raise ValueError("Missing frontend asset")
    return {
        "js": "/static/ui/" + entry["file"],
        "css": ["/static/ui/" + name for name in entry.get("css", [])],
    }


def rewrite_frontend(document: str, assets: dict) -> str:
    """Leave the escaped bootstrap JSON and unrelated HTML byte content untouched."""
    if 'id="cloudbox-data"' not in document and "id='cloudbox-data'" not in document:
        return document
    document = UI_STYLESHEET.sub("", document)
    css = "".join('<link rel="stylesheet" href="' + html.escape(url, quote=True) + '">' for url in assets["css"])
    marker = '<meta name="cloudbox-ui-variant" content="preview">'
    document, heads = re.subn(r"</head\s*>", lambda _: css + marker + "</head>", document, count=1, flags=re.I)
    module = '<script type="module" src="' + html.escape(assets["js"], quote=True) + '"></script>'
    document, modules = UI_MODULE.subn(lambda _: module, document, count=1)
    if heads != 1 or modules != 1:
        raise ValueError("The stable portal did not return a supported CloudBox document")
    return document


def _origin(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("The upstream must be a server-owned HTTP origin")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise ValueError("The upstream must not include a path or query")
    return value.rstrip("/")


def create_app(
    *,
    upstream_url: str = UPSTREAM,
    public_origin: str = PUBLIC_ORIGIN,
    static_dir: Path = DEFAULT_STATIC_DIR,
    transport: httpx.AsyncBaseTransport | None = None,
) -> FastAPI:
    upstream_url = _origin(upstream_url)
    public_origin = _origin(public_origin)
    static_dir = Path(static_dir)
    upstream_origin = urlsplit(upstream_url)

    @asynccontextmanager
    async def lifespan(app):
        frontend_assets(static_dir)
        # Prevent httpx's default cookie persistence from mixing browser sessions.
        async with httpx.AsyncClient(
            transport=transport,
            follow_redirects=False,
            timeout=httpx.Timeout(30.0, connect=5.0),
            cookies=NoCookieJar(),
            trust_env=False,
        ) as client:
            app.state.upstream = client
            yield

    app = FastAPI(title="CloudBox Design Preview", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.mount("/static/ui", StaticFiles(directory=str(static_dir), check_dir=False), name="preview-assets")

    @app.api_route("/healthz", methods=["GET", "HEAD"])
    async def health():
        try:
            frontend_assets(static_dir)
            response = await app.state.upstream.get(upstream_url + "/healthz", headers={"accept-encoding": "identity"})
            response.raise_for_status()
            if response.json().get("status") != "ok":
                raise ValueError("Upstream not ready")
            return {"status": "ok", "variant": "preview"}
        except (httpx.HTTPError, OSError, ValueError, KeyError, TypeError):
            return JSONResponse({"status": "unavailable", "variant": "preview"}, status_code=503)

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
    async def proxy(request: Request, path: str):
        client = app.state.upstream
        raw_headers = request.scope["headers"]
        removed = _removed_headers(raw_headers, REQUEST_REMOVED)
        headers = [(key, value) for key, value in raw_headers if key.lower() not in removed]
        headers.append((b"accept-encoding", b"identity"))
        # copy_with keeps authority fixed even for paths containing scheme-looking text.
        raw_path = request.scope.get("raw_path", request.url.path.encode("utf-8"))
        query = request.scope.get("query_string", b"")
        target = httpx.URL(upstream_url).copy_with(raw_path=raw_path + (b"?" + query if query else b""))
        try:
            upstream_response = await client.request(
                request.method, target, headers=headers, content=await request.body(),
            )
        except httpx.RequestError:
            return JSONResponse(
                {"detail": "CloudBox chưa sẵn sàng. Hãy thử lại sau ít phút."},
                status_code=503,
            )

        content = upstream_response.content
        changed = False
        if "text/html" in upstream_response.headers.get("content-type", "") and b"cloudbox-data" in content:
            try:
                original = content.decode("utf-8")
                content = rewrite_frontend(original, frontend_assets(static_dir)).encode("utf-8")
                changed = content.decode("utf-8") != original
            except (OSError, UnicodeError, ValueError, KeyError, TypeError):
                return JSONResponse(
                    {"detail": "Chưa tải được giao diện thử nghiệm. Hãy kiểm tra bản build."},
                    status_code=502,
                )

        response = Response(content=content, status_code=upstream_response.status_code)
        removed_response = _removed_headers(upstream_response.headers.raw, RESPONSE_REMOVED)
        if changed:
            removed_response |= {b"etag", b"last-modified", b"cache-control"}
        for key, value in upstream_response.headers.raw:
            if key.lower() in removed_response:
                continue
            if key.lower() == b"location":
                location = value.decode("latin-1")
                destination = urlsplit(location)
                # Only internal absolute redirects need a public preview address.
                # Relative redirects and external payment gateways are preserved.
                if destination.scheme in {"http", "https"} and destination.netloc == upstream_origin.netloc:
                    location = public_origin + urlunsplit(("", "", destination.path, destination.query, destination.fragment))
                    value = location.encode("latin-1")
            response.raw_headers.append((key, value))
        if changed:
            response.headers["cache-control"] = "no-store"
        return response

    return app


app = create_app(
    upstream_url=os.environ.get("UPSTREAM_URL", UPSTREAM),
    public_origin=os.environ.get("PREVIEW_PUBLIC_ORIGIN", PUBLIC_ORIGIN),
)
