"""Preview uses the temporary personal vault and does not touch deployed data."""

from base64 import b64decode
from codecs import BOM_UTF16_BE, BOM_UTF16_LE

import pytest

from app.features.storage.collaboration_models import Team
from app.features.storage.preview import TEXT_PREVIEW_LIMIT
from test_native_storage import env, folder, upload


PNG = b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+j9XcAAAAASUVORK5CYII="
)
PDF = b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"


@pytest.mark.parametrize(("name", "content", "media_type"), [
    ("ảnh.png", PNG, "image/png"),
    ("document.pdf", PDF, "application/pdf"),
])
def test_preview_has_verified_type_and_safe_response(env, name, content, media_type):
    client, _ = env
    item, _ = upload(client, name=name, data=content)
    url = f"/api/files/{item['id']}/preview"

    response = client.get(url)
    assert response.status_code == 200
    assert response.content == content
    assert response.headers["content-type"] == media_type
    assert response.headers["content-disposition"].startswith("inline;")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cross-origin-resource-policy"] == "same-origin"
    assert "no-store" in response.headers["cache-control"]
    assert "sandbox" in response.headers["content-security-policy"]
    assert "frame-ancestors 'self'" in response.headers["content-security-policy"]

    head = client.head(url)
    assert head.status_code == 200
    assert head.content == b""
    assert head.headers["content-type"] == media_type
    assert head.headers["content-length"] == str(len(content))
    partial = client.get(url, headers={"Range": "bytes=0-7"})
    assert partial.status_code == 206
    assert partial.content == content[:8]
    download = client.get(f"/api/files/{item['id']}/download")
    assert download.headers["content-disposition"].startswith("attachment;")


@pytest.mark.parametrize("data", [b"Plain text bytes", PDF.split(b"%%EOF", 1)[0]])
def test_preview_rejects_unsupported_or_truncated_content(env, data):
    client, _ = env
    item, _ = upload(client, name="report.pdf", data=data)
    url = f"/api/files/{item['id']}/preview"
    assert client.get(url).status_code == 415
    assert client.head(url).status_code == 415
    assert client.get(f"/api/files/{item['id']}/download").status_code == 200


def test_preview_rechecks_authentication_and_rejects_trashed_files(env):
    client, _ = env
    parent = folder(client)
    item, _ = upload(client, name="ảnh.png", data=PNG, parent=parent)
    url = f"/api/files/{item['id']}/preview"
    assert client.get(f"/api/files/{parent}/preview").status_code == 415

    client.headers["x-test-user"] = "2"
    assert client.get(url).status_code == 404
    assert client.head(url).status_code == 404
    client.headers["x-test-user"] = "3"
    assert client.get(url).status_code == 403
    del client.headers["x-test-user"]
    assert client.get(url).status_code == 401

    client.headers["x-test-user"] = "1"
    assert client.post(f"/api/files/{parent}/trash").status_code == 200
    assert client.get(url).status_code == 404
    assert client.head(url).status_code == 404


def test_personal_preview_hides_team_files_from_team_owner(env):
    client, factory = env
    parent = folder(client, name="Team namespace")
    item, _ = upload(client, name="team.png", data=PNG, parent=parent)
    with factory() as db:
        db.add(Team(owner_id=1, root_id=parent, name="Team"))
        db.commit()

    url = f"/api/files/{item['id']}/preview"
    assert client.get(url).status_code == 404
    assert client.head(url).status_code == 404


def test_text_preview_transcodes_vietnamese_and_preserves_literal_content(env):
    client, _ = env
    text = "Đường dẫn\tNội dung\r\n  <b>Tài liệu Tiếng Việt</b>\n"
    json_text = '{"enabled": true}'
    supported_formats = [
        ("notes.txt", text.encode("utf-8"), text),
        ("README.MD", text.encode("utf-8-sig"), text),
        ("report.csv", BOM_UTF16_LE + text.encode("utf-16-le"), text),
        ("device.log", BOM_UTF16_BE + text.encode("utf-16-be"), text),
        ("settings.json", json_text.encode("utf-8"), json_text),
        ("empty.txt", b"", ""),
    ]
    for name, data, expected in supported_formats:
        item, _ = upload(client, name=name, data=data)
        url = f"/api/files/{item['id']}/preview"
        head = client.head(url)
        assert head.status_code == 200
        assert head.content == b""
        assert head.headers["content-type"] == "text/plain; charset=utf-8"

        response = client.get(url)
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"
        assert response.headers["x-content-type-options"] == "nosniff"
        assert "no-store" in response.headers["cache-control"]
        assert response.text == expected
        assert client.get(f"/api/files/{item['id']}/download").content == data


@pytest.mark.parametrize(("name", "data"), [
    ("binary.txt", b"\xe0\xf2\xff"),
    ("control.log", b"before\x00after"),
    ("excluded.bin", b"File contents"),
])
def test_text_preview_rejects_binary_controls_and_other_extensions(env, name, data):
    client, _ = env
    item, _ = upload(client, name=name, data=data)
    assert client.get(f"/api/files/{item['id']}/preview").status_code == 415
    assert client.get(f"/api/files/{item['id']}/download").content == data


def test_text_preview_enforces_source_byte_limit(env):
    client, _ = env
    part = "ệ".encode("utf-8")
    data = part * (TEXT_PREVIEW_LIMIT // len(part)) + b"a" * (TEXT_PREVIEW_LIMIT % len(part))
    fitting, _ = upload(client, name="fitting.txt", data=data)
    assert client.get(f"/api/files/{fitting['id']}/preview").content == data

    oversized, _ = upload(client, name="oversized.txt", data=data + b"a")
    url = f"/api/files/{oversized['id']}/preview"
    assert client.head(url).status_code == 413
    assert client.get(url).status_code == 413
    assert client.get(f"/api/files/{oversized['id']}/download").content == data + b"a"
