> Đường dẫn đã tổ chức lại ngày01/11/2026. Hướng dẫn hiện hành: README.md tại root; kết quả JSON và ảnh nằm artifacts/. Nội dung mô tả thời điểm QA trước đây vẫn là bằng chứng lịch sử, không mở lại các cổng cũ.

# Khôi phục UI mà giữ dữ liệu và ba cổng cuối

Bản sao trước thay đổi ở `.unified-backup/`; đường dẫn hiện hành trong `.unified-backup/current.txt`. Có từng tệp trước sửa, manifest/SHA256, cấu hình Nextcloud, danh sách app, SQLite Mailpit và image cũ. Thư mục này bị Git ignore; config backup có thể chứa bí mật, không chia sẻ/commit.

## Kiểm tra trước, chưa thay ứng dụng

```powershell
python scripts/rollback-ui.py
```

Script kiểm tra image cũ và Compose dự kiến, chưa đổi UI. Không cần restore toàn database hay ghi đè config.php/.env.

## Về UI gốc

```powershell
python scripts/rollback-ui.py --apply
.\start-local.ps1 -NoBrowser
```

Giữ 8000 / 8080 / 8025, tất cả volume/account/tệp/thư và tuyến public hiện tại. Portal/Mail dùng image gốc đã giữ; Mail vẫn dùng **volume persistent mới**, không quay lại DB /tmp. Nextcloud chỉ disable app theme và trả đúng các khóa branding đã sao lưu. Không mở lại preview; không restore trusted proxies/domain từ snapshot cũ vì tunnel hiện tại có thể khác. Compose rollback bỏ build cho hai image gốc để tránh ghi đè tag backup.

## Áp dụng lại UI mới đã lưu

```powershell
python scripts/rollback-ui.py --new --apply
```

Chỉ có sau khi đã dùng rollback; lấy Compose/branding lưu ngay trước rollback. Source mới và các source preview vẫn được giữ. Muốn build UI mới sau đó dùng `.\start-local.ps1 -Rebuild -NoBrowser`.

Script được kiểm tra cú pháp và validate candidate Compose; không chạy một lần rollback toàn bộ ba UI ở cuối phiên bàn giao. Riêng disable/enable theme và chuyển Mailpit native/custom trên cùng volume đã được chạy thực để đối chiếu; thư QA còn nguyên. Không dùng `docker compose down -v` và không chép ngược SQLite snapshot cũ lên hộp thư đang có thư mới.

## Chạy local thay vì online

```powershell
.\stop-online.ps1
.\start-local.ps1 -NoBrowser
```

stop-online khôi phục địa chỉ local bằng state hiện hành; không xóa .online trước khi stop. Muốn công khai lại chạy start-online.ps1; Quick Tunnel có thể đổi URL khi tạo lại. Laptop cần bật/có mạng, Docker và cloudflared chạy. Chưa chuyển workload sang máy chủ cloud.
