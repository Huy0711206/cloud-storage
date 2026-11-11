> **Tài liệu lịch sử trước chuyển đổi native và xóa source ngày10/11/2026.** Các lệnh/đường dẫn ba dịch vụ bên dưới ghi nhận trạng thái cũ, không chạy trên dự án hiện hành. Xem [README](../../README.md) và [cây hiện hành](../architecture/PROJECT-STRUCTURE.md). Nội dung lịch sử được giữ nguyên bên dưới.

# Kế hoạch tái cấu trúc CloudBox — 01/11/2026

Đã trình bày trước khi thay đổi mã. Mục tiêu giữ hành vi/dữ liệu/ba cổng, không nâng dependency. Root Compose giữ project identity cloud-storage; trạng thái .online/.unified-backup và CSV nghiệp vụ giữ tại chỗ. Source và cả thay đổi chưa commit được snapshot private tại .unified-backup/refactor-20261101; snapshot có .env, không chia sẻ/commit.

## Nguyên nhân và quyết định

Tài liệu quá khứ lẫn hiện tại; source gateway ngừng chạy nằm cạnh app chính; tên preview còn được runtime dùng; script hardcode đường dẫn. Giữ upstream Mailpit nguyên cấu trúc, theme/patch NC nguyên chức năng. Tách domain billing/orders khỏi payment gateway/callback. Không xóa vĩnh viễn source/backup/tài liệu nghi ngờ. Chuyển gateway cũ thành legacy coherent, không xóa toàn bộ preview.

## Cây dự kiến

apps/portal/{frontend,backend,legacy}; apps/nextcloud/{cloudbox_theme,patches}; apps/mail/upstream; packages/design-system; infrastructure/docker/db-init; scripts/{development,operations,maintenance,diagnostics}; docs/{architecture,development,operations,design,qa,history}; artifacts/{qa,design}.

Root giữ README, PROGRESS, Compose và entrypoints start/stop/online. Không tạo test root rỗng; test colocate backend/frontend/native patch. Các root Python/PowerShell script tương thích cũ chỉ dispatch implementation có tổ chức.

## Ánh xạ đợt đầu

| Cũ | Mới |
|---|---|
| portal | apps/portal |
| apps/portal/app | apps/portal/backend/app |
| apps/portal/tests | apps/portal/backend/tests |
| apps/portal/requirements.txt | apps/portal/backend/requirements.txt |
| apps/portal/pytest.ini | apps/portal/backend/pytest.ini |
| nextcloud | apps/nextcloud |
| mail-ui | apps/mail |
| design-system | packages/design-system |
| db-init | infrastructure/docker/db-init |


Đợt kế: feature modules frontend/backend (cập nhật import và test), script implementation dưới scripts, tài liệu dưới docs và JSON/ảnh dưới artifacts. Bảng ánh xạ chi tiết cuối được sinh từ snapshot và nội dung thực tế, không sửa baseline cũ để làm test pass.

## Giữ / hợp nhất / lưu lịch sử / nghi ngờ

- Giữ config/runtime/locks/templates native and vendor tree, .online, .unified-backup, .env, cloudbox-don-hang.csv.
- Hợp nhất hướng dẫn hiện hành vào README/docs; giữ toàn văn README/PROGRESS cũ trong docs/history.
- Lưu legacy: portal/files/mail gateway, wrapper PreviewApp, Dockerfiles/config/tests phụ thuộc. Các renderer preview đang được dùng sẽ được đổi tên/promote, không bỏ.
- Generated: node_modules/dist/cache và CSS/font copies là output, không tự xóa. CSS hash cũ không được manifest hiện tại chọn: giữ và ghi ứng viên dọn sau (cache/rollback).
- Không có tệp nào được chọn xóa vĩnh viễn trong đợt này. Chưa cần câu hỏi người dùng; nếu xóa candidate phải hỏi trước.

## Đường dẫn/rủi ro và kiểm chứng

Compose build/mount, Docker COPY, Python imports/module singleton, Vite entry manifest, font CSS paths, test paths, sync/verify/rollback/online scripts và docs links được cập nhật. Giữ app.main:app, cùng service/volume/network. Nextcloud có thể recreate ngắn để cập nhật theme mount. Giữ online override khi recreate portal.

Kiểm chứng theo đợt: source hash snapshot, Python tests fake SQLite/NC + auth/billing/payment idempotency, frontend typecheck/build và legacy client tests, Mail native build/tests, Compose config quiet, Viewer17 tests/hash/core integrity, health và HTTP local/public. Không thử tài khoản/tệp/thanh toán/email thật.

Rollback cấu trúc: snapshot private + manifest, phục hồi theo đường dẫn cũ có kiểm tra và review diff, không restore toàn DB/volume hay .online. Tài liệu khôi phục chi tiết sẽ ghi cùng trạng thái cuối.
