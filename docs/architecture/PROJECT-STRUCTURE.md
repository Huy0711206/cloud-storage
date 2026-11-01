# Bản đồ dự án CloudBox

## Cây thư mục và trách nhiệm

```text
cloud-storage/
├── apps/
│   ├── portal/
│   │   ├── Dockerfile, .dockerignore
│   │   ├── frontend/
│   │   │   ├── src/main.tsx                    Vite entry cố định
│   │   │   ├── src/app/                        Shell và composition
│   │   │   ├── src/features/
│   │   │   │   ├── authentication/             Login/register/message
│   │   │   │   ├── accounts/                   Thiết lập tài khoản
│   │   │   │   ├── storage/                    Dung lượng/kho tệp
│   │   │   │   ├── billing/                    Gói và đơn hàng
│   │   │   │   ├── payments/                   Checkout dialog
│   │   │   │   ├── administration/             Quản trị
│   │   │   │   ├── dashboard/                  Tổng quan/điều phối section
│   │   │   │   └── public/                     Trang chủ/bảng giá
│   │   │   ├── src/shared/                     Types, theme/forms/formatters
│   │   │   ├── src/components/ui/, hooks/, lib/
│   │   │   ├── src/styles/                     CSS hiện hành và font copies
│   │   │   ├── src/legacy/                     Preview wrapper/Files/Mail cũ
│   │   │   └── tests/, vite*.config.ts         Test và build legacy vẫn giữ
│   │   ├── backend/
│   │   │   ├── app/main.py                    Entrypoint app.main:app
│   │   │   ├── app/core/                      Config/DB/models/security/bootstrap
│   │   │   ├── app/features/
│   │   │   │   ├── authentication/            Đăng ký/verify/login/logout
│   │   │   │   ├── accounts/                  Mật khẩu và dashboard data
│   │   │   │   ├── storage/                   Nextcloud client/provision/quota
│   │   │   │   ├── billing/                   Plans/orders/activation/expiry
│   │   │   │   ├── payments/                  VNPay signing/return/IPN/idempotency
│   │   │   │   ├── administration/            Quyền và quản trị
│   │   │   │   └── public/                    Public home route
│   │   │   ├── app/shared/                    Rendering/frontend bootstrap/mail
│   │   │   ├── app/templates/, app/static/    Shell và fallback còn được giữ
│   │   │   └── tests/, pytest.ini, requirements.txt
│   │   └── legacy/{gateways,docker}/          Không chạy trong Compose hiện hành
│   ├── nextcloud/{cloudbox_theme,patches}/
│   └── mail/{Dockerfile,UPSTREAM.json,upstream/}
├── packages/design-system/                    Tokens/glass/fonts canonical
├── infrastructure/docker/db-init/             Khởi tạo DB lần đầu
├── scripts/
│   ├── development/                          Start local implementation
│   ├── operations/                           Start/stop/status tunnel
│   ├── maintenance/                          Design sync, Viewer/UI rollback, source checks
│   └── diagnostics/                          Verify deployment
├── docs/{architecture,development,operations,design,qa,history}/
├── artifacts/{qa,design}/                    Kết quả/ảnh; không phải runtime state
├── docker-compose.yml                        Root canonical, cùng project identity
├── README.md, PROGRESS.md
├── start-local.cmd, start-local.ps1, start-online.ps1, stop-online.ps1, online.py
└── .env, .online/, .unified-backup/, .runtime/  Private/runtime; Git ignored
```

## Ranh giới nghiệp vụ

Billing quyết định gói, giá, đơn hàng, kỳ hạn, gia hạn và hết hạn. Payments giao tiếp VNPay, kiểm chữ ký/số tiền/trạng thái và idempotency; sau xác nhận gọi billing kích hoạt gói. Storage đồng bộ quota và provision qua client Nextcloud duy nhất. Authentication quản lý đăng ký/xác thực/phiên; accounts sở hữu đổi mật khẩu. ORM models vẫn tập trung vì chỉ ba bảng quan hệ, không cần chia nhỏ giả tạo.

Frontend main→PortalApp→AppShell→feature renderers. Dữ liệu thật và form actions vẫn từ FastAPI, không phát sinh frontend API giả. Tên CSS/data marker preview/unified được giữ để không đổi UI, nhưng các renderer đang chạy đã được promote vào features. Mailpit giữ Vue/Go native, Nextcloud giữ app/volume native, không chuyển thành React gateway.

## Những tệp ở root được giữ có chủ ý

Compose neo project identity/volume/network; đổi vị trí có thể tạo kho dữ liệu khác. Script root là wrapper tương thích để người dùng không đổi lệnh quen thuộc; implementation nằm scripts. .online và .unified-backup được tooling/rollback dùng nên không di chuyển. CSV export nghiệp vụ giữ nguyên chờ quyết định riêng.

## Bản đồ chi tiết

[475 tệp cũ→mới](../../artifacts/qa/refactor-file-map.json), [danh mục và ứng viên dọn](FILE-INVENTORY.md), [bằng chứng source frontend](../../artifacts/qa/refactor-frontend-source.json), [backend](../../artifacts/qa/refactor-backend-semantics.json). Không có dependency nào được nâng trong đợt này.
