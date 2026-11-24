"""Serve supported files inline without relying on filename-derived metadata."""

from os import SEEK_END
import re
from typing import BinaryIO

from fastapi.responses import FileResponse, PlainTextResponse, Response

from .native_models import FileNode
from .native_service import StorageError, blob_path


TEXT_EXTENSIONS = (".txt", ".md", ".csv", ".log", ".json")
TEXT_PREVIEW_LIMIT = 256 * 1024
INVALID_TEXT_CONTROLS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
PREVIEW_HEADERS = {
    "Cache-Control": "private, no-store",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Content-Security-Policy": "sandbox; default-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'self'",
}


def _preview_type(prefix: bytes) -> str | None:
    if prefix.startswith(b"\x89PNG\r\n\x1a\n\x00\x00\x00\x0dIHDR"):
        return "image/png"
    if prefix.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if prefix.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if prefix.startswith(b"RIFF") and prefix[8:16] in (b"WEBPVP8 ", b"WEBPVP8L", b"WEBPVP8X"):
        return "image/webp"
    if re.match(rb"%PDF-(1\.[0-7]|2\.0)[\r\n]", prefix):
        return "application/pdf"
    return None


def _text_preview(source: BinaryIO) -> PlainTextResponse:
    source.seek(0)
    data = source.read(TEXT_PREVIEW_LIMIT + 1)
    if len(data) > TEXT_PREVIEW_LIMIT:
        raise StorageError(413, "Tệp văn bản vượt giới hạn xem trước 256 KiB. Hãy tải tệp xuống.")

    encoding = "utf-16" if data.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
    message = "Không thể đọc tệp dưới dạng văn bản UTF-8 hoặc UTF-16 có BOM. Hãy tải tệp xuống."
    try:
        content = data.decode(encoding)
    except UnicodeDecodeError as exc:
        raise StorageError(415, message) from exc
    if INVALID_TEXT_CONTROLS.search(content):
        raise StorageError(415, message)
    return PlainTextResponse(content, headers={**PREVIEW_HEADERS, "Content-Disposition": "inline"})


def preview_response(node: FileNode) -> Response:
    if node.is_folder:
        raise StorageError(415, "Chỉ hỗ trợ xem trước ảnh, PDF và tệp văn bản.")
    path = blob_path(node.blob_key)
    try:
        with path.open("rb") as source:
            media_type = _preview_type(source.read(16))
            if not media_type and node.name.casefold().endswith(TEXT_EXTENSIONS):
                return _text_preview(source)
            if media_type == "application/pdf":
                size = source.seek(0, SEEK_END)
                source.seek(max(0, size - 1024))
                tail = source.read(1024).rstrip(b"\x00\t\n\f\r ")
                if not tail.endswith((b"\n%%EOF", b"\r%%EOF")):
                    raise StorageError(415, "Tệp PDF chưa đầy đủ để xem trước. Bạn vẫn có thể tải tệp xuống.")
    except FileNotFoundError as exc:
        raise StorageError(503, "Tệp tạm thời không khả dụng. Hãy liên hệ quản trị viên.") from exc
    if not media_type:
        raise StorageError(415, "Không hỗ trợ xem trước nội dung này. Bạn vẫn có thể tải tệp xuống.")
    return FileResponse(
        path,
        media_type=media_type,
        filename=node.name,
        content_disposition_type="inline",
        headers=PREVIEW_HEADERS,
    )
