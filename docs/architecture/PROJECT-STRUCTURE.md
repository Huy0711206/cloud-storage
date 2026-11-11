# Cây hiện hành — 10/11/2026

```text
cloud-storage/
  apps/portal/
    frontend/                 # React, src/main.tsx, check/build chính
    backend/                  # FastAPI, app.main:app
  packages/design-system/     # token/font còn sử dụng
  infrastructure/docker/     # db-init local
  infrastructure/aws/        # Compose production EC2, không có secrets
  scripts/
    development/              # khởi động thủ công
    maintenance/              # sinh thiết kế CloudBox
    operations/one-off/       # tác vụ có điều kiện, không chạy QA
  docs/                       # hiện hành và lịch sử
  artifacts/qa/               # manifest, kiểm thử và fingerprint
  docker-compose.yml          # db/portal, giữ volume/project identity
  docker-compose.named.yml
  start-local.ps1 / .cmd
```

Không còn legacy/, apps/portal/legacy, frontend/src/legacy và optional build configs. Dữ liệu Nextcloud nguồn/volume/database không thuộc các thư mục source đó; vẫn được giữ. Các thư mục private và CSV ở vị trí cũ.

Giữ tên frontend/backend và các features authentication/accounts/storage/billing/payments/administration. Đăng ký thuộc authentication; billing quản lý gói/giá/kỳ hạn, payments giữ giao dịch/chữ ký/callback; Order vẫn ở core.models. Không đổi schema để dọn tên.

migrate.py/rehearse.py và migration metadata giữ để kiểm chứng dữ liệu nguồn. Các báo cáo trước10/11 là lịch sử; danh mục xóa thực tế ở ../../artifacts/qa/deadcode-cleanup-manifest.json, kết quả ở ../../artifacts/qa/deadcode-cleanup-2026-11-10.md.

Đã chốt đường dẫn và lệnh hiện hành ngày10/11/2026: [phát triển](../development/DEVELOPMENT.md), [vận hành](../operations/OPERATIONS.md), [kiểm chứng cuối](../../artifacts/qa/structure-final-2026-11-10.md). Không còn scripts/diagnostics rỗng.

Production từ 10/11/2026 ở AWS Academy EC2; root Compose/start-local là local. Xem [vận hành AWS](../operations/AWS-ACADEMY.md).
