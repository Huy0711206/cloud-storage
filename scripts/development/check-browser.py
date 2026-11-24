"""Verify the exact Portal image in an isolated local browser session."""
import argparse
import json
import secrets
import socket
import subprocess
from time import monotonic, sleep
from http.client import HTTPException
from urllib.request import ProxyHandler, build_opener

from playwright.sync_api import expect, sync_playwright


PASSWORD = "CloudBox-QA-Example-65"
OWNER = "browser-owner@gmail.com"
MEMBER = "browser-member@gmail.com"
SEED = """
from datetime import timedelta
from app.core.database import SessionLocal
from app.core.models import Plan, User, utcnow
from app.core.security import hash_password

with SessionLocal() as db:
    for email, name, code in (
        ("browser-owner@gmail.com", "Chủ kho thử nghiệm", "premium"),
        ("browser-member@gmail.com", "Thành viên thử nghiệm", "free"),
    ):
        plan = db.query(Plan).filter_by(code=code).one()
        expiry = utcnow() + timedelta(days=3) if code == "premium" else None
        db.add(User(email=email, full_name=name, password_hash=hash_password("CloudBox-QA-Example-65"),
                    plan_id=plan.id, plan_expires_at=expiry, is_verified=True))
    db.commit()
"""


def docker(*args):
    return subprocess.run(["docker", *args], text=True, encoding="utf-8",
                          stdout=subprocess.PIPE, check=True, timeout=90).stdout.strip()


def local_url():
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        port = server.getsockname()[1]
    return f"http://127.0.0.1:{port}", port


def wait_ready(base):
    opener = build_opener(ProxyHandler({}))
    deadline = monotonic() + 45
    while monotonic() < deadline:
        try:
            with opener.open(base + "/readyz", timeout=2) as response:
                if json.load(response).get("status") == "ok":
                    return
        except (OSError, HTTPException):
            pass
        sleep(0.35)
    raise RuntimeError("The isolated Portal did not become ready.")


def login(page, base, address):
    page.goto(base + "/login")
    page.locator("#login-email").fill(address)
    page.locator("#login-password").fill(PASSWORD)
    page.get_by_role("button", name="Đăng nhập", exact=True).click()
    page.wait_for_url("**/dashboard**")
    expect(page.locator("#main-content")).to_be_visible(timeout=15000)


def click_button(page, name):
    page.get_by_role("button", name=name, exact=True).click()


def put_file(page, input_name, filename, content):
    page.locator(f'input[aria-label="{input_name}"]').set_input_files(
        dict(name=filename, mimeType="text/plain", buffer=content.encode("utf-8"))
    )
    expect(page.get_by_role("button", name=filename, exact=True)).to_be_visible()


def actions(page, filename, action):
    click_button(page, "Thao tác với " + filename)
    page.get_by_role("menuitem", name=action, exact=True).click()


def personal_flow(page, base, guest):
    page.get_by_role("link", name="Kho lưu trữ", exact=True).click()
    click_button(page, "Thư mục mới")
    page.get_by_label("Tên thư mục").fill("Dự án mẫu")
    click_button(page, "Tạo thư mục")
    click_button(page, "Đánh dấu Dự án mẫu")
    expect(page.get_by_role("button", name="Bỏ đánh dấu Dự án mẫu")).to_be_visible()
    click_button(page, "Dự án mẫu")
    expect(page.get_by_role("navigation", name="Đường dẫn thư mục").get_by_text("Dự án mẫu")).to_be_visible()

    filename, content = "ghi-chu.txt", "Nội dung tiếng Việt"
    put_file(page, "Chọn tệp tải lên", filename, content)
    click_button(page, filename)
    expect(page.get_by_label("Nội dung tệp")).to_have_text(content)
    page.keyboard.press("Escape")
    click_button(page, "Đánh dấu " + filename)
    expect(page.get_by_role("button", name="Bỏ đánh dấu " + filename)).to_be_visible()

    page.get_by_role("link", name="Đã đánh dấu", exact=True).click()
    expect(page.get_by_role("heading", name="Đã đánh dấu")).to_be_visible()
    expect(page.get_by_role("button", name=filename, exact=True)).to_be_visible()
    click_button(page, "Dự án mẫu")
    expect(page.get_by_role("navigation", name="Đường dẫn thư mục").get_by_text("Dự án mẫu")).to_be_visible()

    page.get_by_label("Tìm tệp hoặc thư mục", exact=True).fill("ghi-chu")
    page.get_by_label("Loại tệp").select_option("pdf")
    expect(page.get_by_text("Chưa tìm thấy tệp phù hợp")).to_be_visible()
    page.get_by_label("Loại tệp").select_option("document")
    click_button(page, "Tệp của tôi / Dự án mẫu")
    expect(page.get_by_label("Tìm tệp hoặc thư mục", exact=True)).to_have_value("")
    expect(page.get_by_role("button", name=filename, exact=True)).to_be_visible()

    actions(page, filename, "Chia sẻ")
    click_button(page, "Tạo liên kết chia sẻ")
    share_field = page.get_by_label("Liên kết chỉ đọc")
    expect(share_field).to_be_visible()
    response = guest.goto(share_field.input_value())
    assert response and response.ok, "Public share is unavailable."
    expect(guest.get_by_role("heading", name=filename)).to_be_visible()
    page.keyboard.press("Escape")

    actions(page, filename, "Chuyển vào thùng rác")
    click_button(page, "Chuyển vào thùng rác")
    expect(page.get_by_role("button", name=filename, exact=True)).to_have_count(0)
    page.get_by_role("link", name="Thùng rác", exact=True).click()
    actions(page, filename, "Khôi phục")
    expect(page.get_by_role("button", name=filename, exact=True)).to_have_count(0)
    page.get_by_role("link", name="Đã đánh dấu", exact=True).click()
    expect(page.get_by_role("button", name=filename, exact=True)).to_be_visible()


def team_flow(owner, member, base):
    owner.goto(base + "/dashboard#teams")
    click_button(owner, "Tạo nhóm")
    owner.get_by_label("Tên nhóm").fill("Nhóm QA")
    owner.get_by_role("dialog").get_by_role("button", name="Tạo nhóm", exact=True).click()
    click_button(owner, "Mở không gian")
    put_file(owner, "Chọn tệp cho nhóm", "lich-nhom.txt", "Ghi chú nhóm")
    click_button(owner, "Hoạt động nhóm")
    expect(owner.get_by_role("dialog").get_by_text("lich-nhom.txt", exact=True)).to_be_visible()
    owner.keyboard.press("Escape")
    click_button(owner, "Thành viên")
    owner.get_by_label("Email tài khoản đã xác minh").fill(MEMBER)
    click_button(owner, "Gửi lời mời")
    expect(owner.get_by_role("dialog").get_by_text(MEMBER + " · Đang chờ chấp nhận", exact=True)).to_be_visible()

    login(member, base, MEMBER)
    member.get_by_role("button", name="Thông báo, 1 chưa đọc", exact=True).click()
    expect(member.get_by_role("dialog").get_by_text("Bạn được mời vào nhóm Nhóm QA")).to_be_visible()
    click_button(member, "Đánh dấu đã đọc")
    expect(member.get_by_role("button", name="Đánh dấu đã đọc")).to_have_count(0)
    member.keyboard.press("Escape")
    member.goto(base + "/dashboard#teams")
    click_button(member, "Chấp nhận lời mời")
    click_button(member, "Mở không gian")
    click_button(member, "lich-nhom.txt")
    expect(member.get_by_label("Nội dung tệp")).to_have_text("Ghi chú nhóm")


def check(image, channel):
    base, port = local_url()
    container = docker(
        "run", "-d", "--rm", "-p", f"127.0.0.1:{port}:8000",
        "-e", f"BASE_URL={base}", "-e", "DATABASE_URL=sqlite:////tmp/cloudbox-browser.db",
        "-e", "STORAGE_ROOT=/tmp", "-e", "SECRET_KEY=" + secrets.token_hex(32),
        image,
    )
    try:
        wait_ready(base)
        docker("exec", container, "python", "-c", SEED)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel=channel)
            owner = browser.new_page(viewport={"width": 1280, "height": 900})
            member = browser.new_page(viewport={"width": 390, "height": 844}, has_touch=True)
            guest = browser.new_page()
            for page in (owner, member, guest):
                page.set_default_timeout(12000)
            login(owner, base, OWNER)
            print("Browser: login, personal storage, search, preview, sharing, restore", flush=True)
            personal_flow(owner, base, guest)
            print("Browser: team preview, activity and notifications", flush=True)
            team_flow(owner, member, base)
            browser.close()
        print("Browser checks passed.", flush=True)
    except Exception:
        subprocess.run(["docker", "logs", "--tail", "25", container], check=False, timeout=10)
        raise
    finally:
        subprocess.run(["docker", "rm", "-f", container], check=False, timeout=30)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, help="Local Portal image produced by docker build")
    parser.add_argument("--channel", choices=["msedge", "chrome", "chromium"])
    args = parser.parse_args()
    check(args.image, args.channel)
