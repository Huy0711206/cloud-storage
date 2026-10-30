import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from mail_gateway import create_app, frontend_assets, _origin


@pytest.fixture
def assets(tmp_path):
    (tmp_path / ".vite").mkdir()
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "mail.js").write_text("//mail")
    (tmp_path / "assets" / "mail.css").write_text("body{}")
    (tmp_path / ".vite" / "manifest.json").write_text(json.dumps({"src/mail/main.tsx": {"file": "assets/mail.js", "css": ["assets/mail.css"]}}))
    return tmp_path


@pytest.fixture
def client(assets):
    requests = []

    def handler(request):
        requests.append(request)
        path = request.url.path
        if path.endswith("/part/1.2"):
            return httpx.Response(200, content=b"<script>danger</script>", headers={"content-type": "text/html", "content-disposition": 'inline; filename="report.html"'})
        if path.endswith("/raw"):
            return httpx.Response(200, content=b"Subject: QA\n\nbody", headers={"content-type": "text/plain"})
        if path.endswith("/missing"):
            return httpx.Response(404, text="Not found")
        if request.method in {"PUT", "DELETE"}:
            return httpx.Response(200, text="ok")
        return httpx.Response(200, json={"messages": [], "total": 0, "unread": 0})

    app = create_app(static_dir=assets, transport=httpx.MockTransport(handler))
    with TestClient(app) as test_client:
        yield test_client, requests


def test_spa_assets_and_health(client):
    c, requests = client
    document = c.get("/")
    assert document.status_code == 200
    assert 'lang="vi"' in document.text and "/static/mail/assets/mail.js" in document.text
    assert "script-src 'self'" in document.headers["content-security-policy"]
    assert c.get("/static/mail/assets/mail.js").status_code == 200
    assert c.get("/static/mail/missing.js").status_code == 404
    assert c.get("/healthz").json()["status"] == "ok"
    assert requests[-1].url.path == "/api/v1/messages"


def test_list_search_fixed_upstream(client):
    c, requests = client
    assert c.get("/api/v1/search", params={"query": "is:unread from:cloudbox", "limit": 20, "start": 0}).status_code == 200
    assert requests[-1].url.host == "mailpit"
    assert requests[-1].url.params["query"] == "is:unread from:cloudbox"
    assert c.get("/api/v1/messages?url=http://evil.test").status_code == 422
    assert c.get("/api/v1/messages?start=-1").status_code == 422
    assert c.get("/api/v1/messages?limit=9999").status_code == 422
    assert c.get("/api/v1/search").status_code == 422


@pytest.mark.parametrize("method,path", [("post", "send"), ("post", "message/abc/release"), ("get", "message/abc/link-check"), ("get", "info"), ("delete", "search?query=all")])
def test_unsupported_features_are_not_proxied(client, method, path):
    c, requests = client
    assert getattr(c, method)("/api/v1/" + path).status_code in {404, 405}
    assert not requests


@pytest.mark.parametrize("method,data", [("put", {}), ("delete", {}), ("delete", {"IDs": []}), ("put", {"IDs": ["abc"], "Read": "yes"}), ("put", {"IDs": ["abc"], "Read": True, "Search": "all"}), ("delete", {"IDs": ["../x"]})])
def test_require_explicit_valid_message_ids(client, method, data):
    c, requests = client
    assert c.request(method.upper(), "/api/v1/messages", json=data).status_code == 422
    assert not requests


def test_valid_mark_and_delete(client):
    c, requests = client
    assert c.put("/api/v1/messages", json={"IDs": ["qa_ABC-1"], "Read": False}).status_code == 200
    assert json.loads(requests[-1].content) == {"IDs": ["qa_ABC-1"], "Read": False}
    assert c.request("DELETE", "/api/v1/messages", json={"IDs": ["qa_ABC-1"]}).status_code == 200


def test_cross_site_and_foreign_origin_are_blocked(client):
    c, requests = client
    assert c.get("/api/v1/message/abc", headers={"sec-fetch-site": "cross-site"}).status_code == 403
    assert c.put("/api/v1/messages", headers={"origin": "https://evil.test"}, json={"IDs": ["abc"], "Read": True}).status_code == 403
    assert c.put("/api/v1/messages", headers={"origin": "http://testserver"}, json={"IDs": ["abc"], "Read": True}).status_code == 200
    assert len(requests) == 1


def test_download_is_attachment_and_nosniff(client):
    c, requests = client
    response = c.get("/api/v1/message/abc/part/1.2")
    assert response.content == b"<script>danger</script>"
    assert response.headers["content-type"] == "application/octet-stream"
    assert response.headers["content-disposition"] == 'attachment; filename="report.html"'
    assert response.headers["x-content-type-options"] == "nosniff"
    assert c.get("/api/v1/message/abc/raw?dl=1").headers["content-disposition"] == 'attachment; filename="abc.eml"'


def test_api_errors_and_no_relay_redirect(assets):
    def handler(request):
        if request.url.path.endswith("/messages"):
            raise httpx.ConnectError("offline", request=request)
        return httpx.Response(302, headers={"location": "https://external.test"})
    with TestClient(create_app(static_dir=assets, transport=httpx.MockTransport(handler))) as c:
        assert c.get("/api/v1/messages").status_code == 503
        assert c.get("/healthz").status_code == 503
        assert c.get("/api/v1/message/abc").status_code == 502


@pytest.mark.parametrize("value", ["file:///etc", "http://user:pw@host", "https://host/path", "https://host?target=x"])
def test_upstream_must_be_origin(value):
    with pytest.raises(ValueError):
        _origin(value)


def test_manifest_rejects_escape(assets):
    (assets / ".vite" / "manifest.json").write_text(json.dumps({"src/mail/main.tsx": {"file": "../outside.js"}}))
    with pytest.raises(ValueError):
        frontend_assets(assets)


def test_no_shared_cookie_and_unexpected_html_is_plain_text(assets):
    seen = []
    def handler(request):
        seen.append(request.headers.get("cookie"))
        return httpx.Response(500, text="<script>unexpected()</script>", headers={"content-type": "text/html", "set-cookie": "upstream-session=private; Path=/"})
    with TestClient(create_app(static_dir=assets, transport=httpx.MockTransport(handler))) as c:
        first = c.get("/api/v1/messages", headers={"cookie": "user-session=private"})
        second = c.get("/api/v1/messages")
        assert seen == [None, None]
        assert first.headers["content-type"].startswith("text/plain")
        assert "set-cookie" not in first.headers


def test_encoded_escape_path_never_reaches_upstream(client):
    c, requests = client
    for path in ["message/abc/part/%2e%2e", "message/abc%2F..%2Fsend", "http://external.test/api/v1/messages"]:
        assert c.get("/api/v1/" + path).status_code == 404
    assert not requests
