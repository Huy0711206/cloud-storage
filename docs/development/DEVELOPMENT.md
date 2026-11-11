# Phát triển và kiểm thử CloudBox

Source hiện hành: apps/portal/frontend (React), apps/portal/backend (FastAPI app.main:app). Đăng ký/OTP tại authentication; tài khoản tại accounts; kho tại storage; gói/giá tại billing; callback/chữ ký/giao dịch tại payments; quản trị tại administration. Không còn source/build/test gateway hoặc Mailpit/Nextcloud.

## Frontend

Từ root dự án:

```powershell
Set-Location apps/portal/frontend
pnpm install --frozen-lockfile --ignore-scripts
pnpm check
pnpm build
```

Giữ packageManager pnpm11.25.0 và pnpm-lock.yaml. Không pnpm update để chữa lỗi đường dẫn. node_modules là output cài đặt: nếu đã di chuyển checkout, kiểm junction/virtualStoreDir và cài lại đúng frozen lockfile tại vị trí mới, không sửa thủ công metadata để che lỗi. Trong môi trường kiểm thử không tương tác, đặt CI=true chỉ cho tiến trình cài đặt. Không vô hiệu hóa kiểm tra supply-chain; offline có thể thiếu metadata dù artifact đã cache. Không pin/nâng/hạ dependency trong đợt kiểm cấu trúc.

Vite dùng src/main.tsx, dist/.vite/manifest.json và /static/ui/. Frontend .gitignore giữ node_modules/dist/tsbuildinfo ngoài Git. Token/font ở packages/design-system; scripts/sync-design.py chuyển tới maintenance/sync-design.py và CHỈ sinh tài nguyên CloudBox, đây là tác vụ ghi source có chủ đích, không phải lệnh test.

## Backend

Từ root, trong môi trường QA đã cài requirements và pytest:

```powershell
Set-Location apps/portal/backend
python -m pytest -q
```

Mặc định dùng SQLite/tệp/SMTP/thanh toán giả; PostgreSQL-only tests bỏ qua nếu chưa cung cấp TEST_POSTGRES_URL. Concurrency chỉ chạy trên DB dùng một lần có tên cloudbox_qa; không dùng .env/DATABASE_URL production làm test URL:

```powershell
python -m pytest -q tests/test_native_postgres.py tests/test_storage_lifecycle_postgres.py
```

Lệnh thứ hai cần TEST_POSTGRES_URL trỏ DB QA đã chuẩn bị riêng. Không gửi SMTP/Gmail hoặc chạy payment/migration thật để kiểm thử cấu trúc. pytest là dependency QA, không thêm runtime chỉ để chạy test. Python requirements hiện dùng khoảng phiên bản; kế hoạch khóa dependency dựa trên runtime đã kiểm chứng là bước tiếp theo, chưa làm ở đây.

## Quy trình hiện hành

Sau thay đổi: chạy kiểm tra liên quan; typecheck/build nếu chạm frontend; QA riêng nếu chạm backend. Đối chiếu mount/dữ liệu và chỉ cập nhật Portal nếu runtime đổi. Build không đồng nghĩa đã deploy. Tài liệu khôi phục ba dịch vụ và verifier cũ là lịch sử, không chạy theo.

Xem [vận hành](../operations/OPERATIONS.md), [cấu trúc](../architecture/PROJECT-STRUCTURE.md), [kiểm chứng nguồn](../../artifacts/qa/deadcode-cleanup-2026-11-10.md).
