# Vận hành CloudBox

Ba cổng web:8000 portal,8080 Nextcloud,8025 Mailpit loopback. DB/Redis/SMTP nội bộ; không mở8001/8081/8026.

## Khởi chạy và build

Từ root: `.\start-local.cmd` hoặc `.\start-local.ps1 -NoBrowser`. Build lại cả portal/Mail bằng `-Rebuild`, chỉ Mail bằng `-RebuildMail`. Compose vẫn ở root; giữ tên service và volume. Sau build phải chạy start-local để recreate image mới, không nhầm build thành deploy.

## Trạng thái online cuối đợt

**Người dùng đã chọn giữ tunnel tắt, hoàn tất kiểm local.** Docker bị dừng khi công việc gián đoạn; đã bật Docker lại và chạy stop-online để khôi phục Nextcloud/portal về local. Không tạo tunnel/domain mới. Trạng thái cũ được lưu .online/last-session.json và last-compose.json, không hardcode URL tạm cũ vào source.

`python online.py status` báo không có active saved session. Chỉ bật lại bằng start-online khi người dùng cần; Quick Tunnel có thể đổi URL. Khi online, start-local giữ HTTPS override và cần dùng URL HTTPS để login portal. Khi dừng online, script nay archive compose.json thành last-compose.json để lần chạy local không nhầm override cũ là phiên còn hoạt động. Đây là sửa thao tác trạng thái có kiểm thử dữ liệu giả, không đổi nghiệp vụ.

## Kiểm tra / log

```powershell
docker compose config --quiet
docker compose ps
python scripts/verify-ui.py
python scripts/patch-viewer.py
```

Log trực tiếp dùng docker compose logs --tail; không chia sẻ nguyên log/config chứa secret. .env/.online/.unified-backup/.runtime bị ignore. Giữ máy bật và Docker chạy; Mailpit dùng volume persistent cloud-storage_mailpit_data. Không down -v.

## Khôi phục

[Rollback UI](ROLLBACK-UI.md) chỉ chuyển image/theme, giữ ports/data. Viewer riêng: `python scripts/patch-viewer.py --restore` trả signed app về gốc nhưng lỗi legacy có thể quay lại. Chữ ký app hiện tại báo đúng loader/hash module của bản vá; không tắt integrity.

[Rollback cấu trúc](REFACTOR-ROLLBACK.md) dùng source ZIP trước refactor, không restore DB hay trạng thái online cũ. Dockerfiles/source legacy là tư liệu/build test; không thêm service Compose để mở cổng đã ngừng.
