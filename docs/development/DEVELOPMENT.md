# Phát triển và kiểm thử

Chạy từ root để dùng Compose/entrypoints. Frontend development tools nằm apps/portal/frontend; backend tools nằm apps/portal/backend. Không sửa source upstream Mailpit hoặc bộ font canonical rồi quên sync/build.

## Frontend

```powershell
Set-Location apps/portal/frontend
pnpm install --frozen-lockfile
pnpm check
pnpm build
pnpm test:mail
# Chỉ kiểm tra build legacy, không mở cổng cũ:
pnpm build:files
pnpm exec vite build --config vite.mail.config.ts
```

Giữ pnpm-lock.yaml và packageManager hiện hành. Không chạy update để xử lý lỗi đường dẫn. Windows pnpm có thể dùng junction tuyệt đối; khi di chuyển checkout, cài lại dependency tại vị trí mới và kiểm tra junction target, không xóa nguồn hoặc đổi lock để che lỗi.

## Backend

requirements.txt nằm apps/portal/backend. Package vẫn là app, chạy từ backend bằng `uvicorn app.main:app`. Biến cấu hình phải được thiết lập theo môi trường, không đưa secret vào source. Test_flow thiết lập SQLite tạm trước import app, thay Nextcloud bằng FakeNC và email bằng bộ ghi giả.

```powershell
Set-Location apps/portal/backend
python -m pytest -q
```

Cần môi trường đã cài runtime requirements và pytest; pytest là dependency kiểm thử, không thêm vào runtime chỉ để thuận tiện. Lệnh container cô lập thực tế nằm [backend test report](../../artifacts/qa/refactor-backend-tests.json): network none, nguồn read-only và tmpfs /tmp. Không dùng database portal thật để chạy test.

## Kiểm chứng nguồn sau di chuyển

Từ root:

```powershell
python scripts/maintenance/verify-backend-refactor.py
python scripts/maintenance/verify-frontend-refactor.py
node --test apps/nextcloud/patches/viewer-close/viewer-close.test.mjs
python scripts/maintenance/sync-design.py
python scripts/diagnostics/verify-ui.py
```

Hai source checker chỉ phục vụ đối chiếu đợt refactor với snapshot gốc. Chúng cố ý phát hiện source đổi sau review; khi thêm nghiệp vụ mới phải review/chuyển baseline có giải thích, không sửa hash để ép pass. Chúng không thay thế tests/runtime QA.

## Chỉnh theo nghiệp vụ

- Đăng ký/login: frontend features/authentication và backend features/authentication.
- Gói/đơn hàng: features/billing; callback/chữ ký/idempotency: features/payments.
- Kho/quota: features/storage và Nextcloud native.
- Mail gửi từ shared/mailer; không thêm provider/email ngoài để thử.
- Giao diện dùng token ở packages/design-system, sync rồi build ứng dụng.

Không sửa JSX, giá, quyền hoặc route chỉ vì đổi thư mục. Các cảnh báo dynamic import không tách chunk và TestClient/httpx deprecation được ghi nhận riêng; chưa nâng dependency để loại cảnh báo.
