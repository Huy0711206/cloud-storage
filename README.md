# CloudBox

Cổng dịch vụ Cloud Data Storage, kho tệp Nextcloud và hộp thư thử Mailpit. Dự án được tổ chức lại ngày 01/11/2026; không đổi các cổng, dữ liệu hay nghiệp vụ.

| Địa chỉ | Vai trò |
|---|---|
| http://localhost:8000 | CloudBox: đăng ký, tài khoản, gói dịch vụ, đơn hàng, thanh toán và quản trị |
| http://localhost:8080 | Nextcloud native đầy đủ, theme CloudBox và bản vá Viewer |
| http://localhost:8025 | Mailpit native đầy đủ; chỉ loopback/local |

8001, 8081, 8026 đã ngừng, không thuộc quy trình chạy hiện hành.

## Khởi chạy

Từ thư mục gốc, Docker Desktop đang chạy:

```powershell
.\start-local.cmd
# Sau khi sửa frontend/backend:
.\start-local.ps1 -Rebuild -NoBrowser
# Chỉ build Mail:
.\start-local.ps1 -RebuildMail -NoBrowser
python online.py status
```

Nếu PowerShell chặn script, dùng `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\start-local.ps1 -NoBrowser`; không đổi chính sách toàn máy.

Khi đang online, start-local giữ override HTTPS hiện hành. Dùng URL public để đăng nhập portal vì cookie Secure. Muốn trở về local: `.\stop-online.ps1`, rồi `.\start-local.ps1 -NoBrowser`. Bật công khai khi cần bằng `.\start-online.ps1`. Không công khai Mail/DB/Redis.

Laptop phải bật/có mạng, Docker và cloudflared chạy; Quick Tunnel có thể đổi URL khi tạo lại. Đây vẫn là ứng dụng trên laptop, chưa chuyển lên máy chủ cloud. Không xóa `.online/` khi tunnel đang hoạt động.

## Cấu trúc

```text
apps/
  portal/
    frontend/             React/TypeScript, feature UI và shared components
    backend/              FastAPI app, domain features, templates và tests
    legacy/               Các gateway/bản thử không chạy trong Compose
  nextcloud/              Theme và bản vá có kiểm soát; native data nằm trong volume
  mail/upstream/          Source Mailpit vendor nguyên cấu trúc
packages/design-system/   Tokens, fonts và nền tảng giao diện dùng chung
infrastructure/docker/   Khởi tạo database
scripts/                  development, operations, maintenance, diagnostics
docs/                     Kiến trúc, phát triển, vận hành, thiết kế, QA, lịch sử
artifacts/                Bằng chứng QA, ảnh và mockup
```

Compose và các lệnh khởi chạy quen thuộc vẫn ở root. `.env`, `.online/`, `.unified-backup/` là private/runtime, không phải source để chia sẻ. `cloudbox-don-hang.csv` được giữ tại chỗ vì là export nghiệp vụ, chưa có yêu cầu xử lý.

## Đọc tài liệu

- [Tiến độ và bàn giao](PROGRESS.md)
- [Bản đồ kiến trúc và nghiệp vụ](docs/architecture/PROJECT-STRUCTURE.md)
- [Kế hoạch và ánh xạ tái cấu trúc](docs/architecture/REFACTOR-PLAN.md)
- [Phát triển và kiểm thử](docs/development/DEVELOPMENT.md)
- [Vận hành và khôi phục](docs/operations/OPERATIONS.md)
- [Thiết kế](docs/design/DESIGN-SYSTEM.md)
- [Chẩn đoán hiện hành](docs/qa/DIAGNOSTICS-2026-11-01.md)
- [Danh mục tệp và ứng viên dọn](docs/architecture/FILE-INVENTORY.md)
- [Tài liệu cũ nguyên bản](docs/history/README-before-refactor.md)

## Trạng thái lỗi đã biết

Viewer đã vá tương thích hai fallback Sidebar, có backup/hash và 17 regression tests; app integrity báo đúng loader/module đã sửa, không tắt kiểm tra chữ ký. Lõi Nextcloud kiểm riêng. Xem [bản vá](apps/nextcloud/patches/viewer-close/README.md).

Kết luận phiên bản404 cũ đã hiệu chỉnh: bản hiện tại dùng files DAV, bản lịch sử dùng archive DAV; bài thử cũ gọi sai loại URL. Lỗi MutationObserver đã tái hiện trên iframe tĩnh không có Mailpit/JavaScript, chưa xác định chính xác thành phần môi trường browser. HTTPS từng có ngắt tải font tạm thời; kiểm lại đủ byte/hash đạt. Không tuyên bố toàn hệ thống không lỗi hoặc đã thử đầy đủ mọi app/tệp lớn/2FA/thanh toán thật.
