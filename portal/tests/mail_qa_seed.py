"""Seed only the disposable CloudBox Mail QA inbox; never the real Mailpit.

Run in a container on cloud-storage_default while cloudbox-mail-qa is running.
The hostname guard intentionally prevents this fixture from targeting mailpit.
"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import format_datetime, make_msgid
import os
import smtplib


QA_HOST = "cloudbox-mail-qa"
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+ip1sAAAAASUVORK5CYII="
)


def message(subject: str, sender: str = "CloudBox QA <cloudbox-qa@qa.test>") -> EmailMessage:
    mail = EmailMessage()
    mail["From"] = sender
    mail["To"] = "Minh Anh QA <minhanh@qa.test>"
    mail["Subject"] = subject
    mail["Date"] = format_datetime(datetime.now(timezone.utc))
    mail["Message-ID"] = make_msgid(domain="qa.test")
    mail["X-CloudBox-Test"] = "disposable-mail-qa-only"
    return mail


def fixtures() -> list[EmailMessage]:
    plain = message("[QA] Xác thực tài khoản CloudBox — thư mẫu")
    plain.set_content(
        "Xin chào Minh Anh,\n\n"
        "Đây là dữ liệu kiểm thử giao diện trong hộp thư QA tạm.\n"
        "Liên kết minh họa sau không thể kích hoạt tài khoản thật:\n"
        "https://example.invalid/verify?token=INVALID-QA-ONLY\n\n"
        "Không cần mở liên kết. Thư này không được gửi ra Internet.\n\nCloudBox QA\n"
    )

    rich = message("[QA] Tài liệu dự án đã sẵn sàng", "Nhóm dự án CloudBox <duan@qa.test>")
    rich["Cc"] = "Giảng viên QA <giangvien@qa.test>"
    rich.set_content(
        "Xin chào Minh Anh,\n\nTài liệu mẫu đã sẵn sàng để bạn kiểm tra hiển thị, "
        "ảnh nội tuyến và tải tệp đính kèm.\n\nĐây là dữ liệu QA, không phải thông báo thật.\n"
    )
    rich.add_alternative(
        '<!doctype html><html lang="vi"><head><meta charset="utf-8">'
        '<style>body{font-family:Arial,sans-serif;color:#13233a;background:#f5f7fb;padding:24px}'
        '.letter{background:white;border:1px solid #e0e6ef;border-radius:12px;padding:28px;max-width:540px}'
        'h1{font-size:24px;color:#335cff}p{line-height:1.7}</style></head><body>'
        '<article class="letter"><img src="cid:qa-pixel" alt="Ảnh nội tuyến QA" width="28" height="28">'
        '<h1>Tài liệu đã sẵn sàng</h1><p>Xin chào Minh Anh,</p>'
        '<p>Đây là mẫu <strong>HTML tiếng Việt</strong> để kiểm tra nội dung email. '
        'Bạn có thể xem bản văn bản hoặc tải tài liệu đính kèm bên dưới.</p>'
        '<p>Thư này chỉ nằm trong hộp thư QA tạm.</p><p>CloudBox QA</p></article></body></html>',
        subtype="html",
    )
    rich.get_payload()[-1].add_related(PNG, maintype="image", subtype="png", cid="<qa-pixel>", filename="qa-pixel.png")
    rich.add_attachment(
        "TÀI LIỆU KIỂM THỬ CLOUDBOX MAIL\n\n"
        "Nội dung này chỉ dùng để xác minh tải tệp đính kèm và mã hóa UTF-8.\n"
        "Không chứa thông tin tài khoản hoặc mật khẩu.\n",
        subtype="plain", filename="huong-dan-qa.txt",
    )

    hostile = message(
        "[QA] Kiểm tra cô lập HTML — tiêu đề dài với tiếng Việt và đường dẫn để kiểm tra xuống dòng trên màn hình nhỏ",
        "Bộ kiểm thử bảo vệ vùng đọc thư có tên dài <isolation-check@qa.test>",
    )
    hostile.set_content("Đây là thư QA kiểm tra cô lập nội dung HTML. Không có liên kết cần mở.\n")
    hostile.add_alternative(
        '<!doctype html><html><head><meta http-equiv="refresh" content="0;url=https://example.invalid/refresh">'
        '<base href="https://example.invalid/"><style>'
        '@import url("https://example.invalid/font.css");'
        'body{font-family:Arial,sans-serif} .danger{background-image:url(https://example.invalid/css-pixel.png)}'
        '</style></head><body>'
        '<h1>Kiểm tra cô lập nội dung</h1><p>Đoạn văn này phải đọc được.</p>'
        '<p>Script, điều hướng tự động và ảnh ngoài phải bị chặn.</p>'
        '<script>parent.document.body.dataset.mailQaScriptExecuted="yes";</script>'
        '<img src="https://example.invalid/track.png" onerror="parent.document.body.dataset.mailQaEventExecuted=\"yes\"" alt="Ảnh ngoài cần bị chặn">'
        '<div class="danger" style="background:url(https://example.invalid/inline-css.png)">Nội dung còn lại vẫn đọc được.</div>'
        '<a href="https://example.invalid/verify?token=QA-NEVER-OPEN">Liên kết không được tự mở</a>'
        '<form action="https://example.invalid/submit"><input name="secret"><button>Gửi</button></form>'
        '<iframe src="https://example.invalid/frame"></iframe>'
        '<svg onload="parent.document.body.dataset.mailQaSvgExecuted=\"yes\""></svg>'
        '</body></html>', subtype="html",
    )
    return [plain, rich, hostile]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--new-message", action="store_true", help="Send one additional arrival for polling QA.")
    args = parser.parse_args()
    host = os.environ.get("MAIL_QA_SMTP_HOST", QA_HOST)
    if host != QA_HOST:
        raise SystemExit("Refusing to seed any inbox except cloudbox-mail-qa.")
    if args.new_message:
        mail = message("[QA] Thư mới vừa đến — " + datetime.now(timezone.utc).strftime("%H:%M:%S"))
        mail.set_content("Thư QA bổ sung để kiểm tra cập nhật hộp thư mà không tải lại trang.\n")
        mails = [mail]
    else:
        mails = fixtures()
    with smtplib.SMTP(host, 1025, timeout=15) as client:
        for mail in mails:
            client.send_message(mail)
    print(f"Seeded {len(mails)} local QA message(s) into {QA_HOST}; no Internet delivery.")


if __name__ == "__main__":
    main()
