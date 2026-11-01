"""The design gateway must isolate frontend assets without duplicating account state."""
import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from legacy.gateways.preview import create_app, rewrite_frontend

DOCUMENT = """<!doctype html><html><head>
<link rel="stylesheet" href="/static/ui/assets/main-stable.css">
<link rel="stylesheet" href="/static/keep.css"></head><body>
<script id="cloudbox-data" type="application/json">{"full_name":"QA \\u003c/script\\u003e","page":"dashboard"}</script>
<script type="module" src="/static/ui/assets/main-stable.js"></script></body></html>"""


@pytest.fixture
def assets(tmp_path):
    (tmp_path / ".vite").mkdir()
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "preview.js").write_text("console.log('preview')")
    (tmp_path / "assets" / "preview.css").write_text("body{color:blue}")
    (tmp_path / ".vite" / "manifest.json").write_text(json.dumps({
        "src/main.tsx": {"file": "assets/preview.js", "css": ["assets/preview.css"]}
    }))
    return tmp_path


def test_html_only_replaces_asset_tags_preserving_bootstrap_and_status(assets):
    def handler(request):
        assert request.url.host == "portal"
        assert request.headers["accept-encoding"] == "identity"
        return httpx.Response(400, text=DOCUMENT, headers={
            "content-type": "text/html; charset=utf-8",
            "etag": "stable-html-etag",
            "cache-control": "max-age=100",
        })
    with TestClient(create_app(static_dir=assets, transport=httpx.MockTransport(handler))) as client:
        response = client.get("/login")
    assert response.status_code == 400
    assert "main-stable" not in response.text
    assert "/static/ui/assets/preview.js" in response.text
    assert "/static/ui/assets/preview.css" in response.text
    assert "/static/keep.css" in response.text
    assert '{"full_name":"QA \\u003c/script\\u003e","page":"dashboard"}' in response.text
    assert 'content="preview"' in response.text
    assert response.headers["cache-control"] == "no-store"
    assert "etag" not in response.headers


def test_forms_redirects_and_multiple_set_cookie_pass_through(assets):
    seen = []
    def handler(request):
        seen.append(request)
        return httpx.Response(303, headers=[
            ("location", "/dashboard"),
            ("set-cookie", "session=signed-user-a; Path=/; HttpOnly; SameSite=Lax"),
            ("set-cookie", "another=value; Path=/; HttpOnly"),
        ])
    with TestClient(create_app(static_dir=assets, transport=httpx.MockTransport(handler))) as client:
        response = client.post("/login", content=b"email=test%40example.test&password=private",
                               headers={"content-type": "application/x-www-form-urlencoded", "cookie": "session=old"},
                               follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"
    assert len(response.headers.get_list("set-cookie")) == 2
    assert seen[0].content == b"email=test%40example.test&password=private"
    assert seen[0].headers["cookie"] == "session=old"


def test_gateway_does_not_retain_cookie_between_visitors(assets):
    seen_cookies = []
    def handler(request):
        seen_cookies.append(request.headers.get("cookie"))
        return httpx.Response(200, text="ok", headers={"set-cookie": "session=private-a; Path=/"})
    with TestClient(create_app(static_dir=assets, transport=httpx.MockTransport(handler))) as client:
        client.get("/one", headers={"cookie": "session=visitor-a"})
        client.cookies.clear()
        client.get("/two")
    assert seen_cookies == ["session=visitor-a", None]


@pytest.mark.parametrize("location,expected", [
    ("/dashboard", "/dashboard"),
    ("https://sandbox.vnpayment.vn/pay?order=1", "https://sandbox.vnpayment.vn/pay?order=1"),
    ("http://portal:8000/dashboard?ok=1", "http://localhost:8001/dashboard?ok=1"),
])
def test_redirect_destinations(assets, location, expected):
    def handler(request):
        return httpx.Response(303, headers={"location": location})
    with TestClient(create_app(static_dir=assets, transport=httpx.MockTransport(handler))) as client:
        response = client.get("/redirect", follow_redirects=False)
    assert response.headers["location"] == expected


def test_static_assets_are_served_without_touching_backend(assets):
    def handler(request):
        raise AssertionError("Static requests must not reach stable backend")
    with TestClient(create_app(static_dir=assets, transport=httpx.MockTransport(handler))) as client:
        assert client.get("/static/ui/assets/preview.js").status_code == 200
        assert client.get("/static/ui/assets/preview.css").status_code == 200
        assert client.get("/static/ui/assets/main-stable.js").status_code == 404
        assert client.get("/static/ui/%2e%2e/preview.py").status_code != 200


def test_health_requires_backend_and_frontend(assets):
    def healthy(request):
        assert request.url.path == "/healthz"
        return httpx.Response(200, json={"status": "ok"})
    with TestClient(create_app(static_dir=assets, transport=httpx.MockTransport(healthy))) as client:
        response = client.get("/healthz")
        assert response.json() == {"status": "ok", "variant": "preview"}
        (assets / "assets" / "preview.js").unlink()
        assert client.get("/healthz").status_code == 503


def test_upstream_failure_is_clear_and_does_not_expose_details(assets):
    def unavailable(request):
        raise httpx.ConnectError("sensitive-internal-host-and-credentials", request=request)
    with TestClient(create_app(static_dir=assets, transport=httpx.MockTransport(unavailable))) as client:
        response = client.get("/dashboard")
        health = client.get("/healthz")
    assert response.status_code == health.status_code == 503
    assert "sensitive-internal" not in response.text


def test_fixed_origin_hop_headers_and_query_encoding(assets):
    seen = []
    def handler(request):
        seen.append(request)
        return httpx.Response(200, text="ok", headers=[
            ("connection", "x-internal"),
            ("x-internal", "do-not-forward"),
            ("keep-alive", "timeout=10"),
        ])
    with TestClient(create_app(static_dir=assets, transport=httpx.MockTransport(handler))) as client:
        response = client.get("/http://other.example/private?q=a%2Bb&token=x%3Dy",
                              headers={"connection": "x-private", "x-private": "removed",
                                       "x-forwarded-host": "other.example", "host": "other.example"})
        assert client.request("TRACE", "/anything").status_code == 405
    assert seen[0].url.host == "portal"
    assert seen[0].url.path == "/http://other.example/private"
    assert seen[0].url.query == b"q=a%2Bb&token=x%3Dy"
    assert "x-private" not in seen[0].headers
    assert "x-forwarded-host" not in seen[0].headers
    assert "x-internal" not in response.headers
    assert "keep-alive" not in response.headers


def test_non_cloudbox_html_is_not_rewritten():
    original = '<html><head></head><body>Unrelated error page</body></html>'
    assert rewrite_frontend(original, {"js": "/preview.js", "css": []}) == original


def test_upstream_must_be_an_origin(assets):
    with pytest.raises(ValueError):
        create_app(upstream_url="https://user:secret@other.example/private", static_dir=assets)
