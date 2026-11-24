# Phát triển và kiểm thử CloudBox

Source hiện hành: apps/portal/frontend (React), apps/portal/backend (FastAPI app.main:app). Đăng ký/OTP tại authentication; tài khoản tại accounts; kho tại storage; gói/giá tại billing; callback/chữ ký/giao dịch tại payments; quản trị tại administration. Không còn source/build/test gateway hoặc Mailpit/Nextcloud.

## Kiểm tra trước khi gửi bản mới

Chuẩn bị Python 3.12 với các thư viện kiểm thử và Node.js 24 với pnpm 11.25.0. Từ thư mục gốc, chạy trong PowerShell.

```powershell
python -m pip install -r apps/portal/backend/requirements.txt pytest
.\scripts\development\check.ps1
```

Nếu dùng một môi trường Python riêng, truyền đường dẫn chương trình Python qua `-PythonExecutable`. Script chạy pytest, cài frontend theo lockfile, kiểm tra TypeScript, chạy kiểm thử tải lên bằng Node và build giao diện. Các bài mặc định dùng SQLite, tệp tạm và dịch vụ giả. Lỗi ở bất kỳ bước nào đều làm lệnh trả mã khác 0. Workflow **CloudBox checks** chạy cùng lệnh khi mở hoặc cập nhật pull request.

## Kiểm thử trên trình duyệt

Trên **laptop**, mở Docker Desktop và chạy trong PowerShell 7 tại thư mục dự án.

```powershell
python -m pip install -r scripts/development/browser-requirements.txt
docker build --platform linux/amd64 -t cloudbox-portal:browser-qa ./apps/portal
python -X utf8 scripts/development/check-browser.py --image cloudbox-portal:browser-qa --channel msedge
```

Luồng Playwright mở Portal trong container tạm trên cổng loopback ngẫu nhiên, với tài khoản giả, SQLite và tệp mẫu trong container. Bài thử kiểm tra đăng nhập, tải lên, xem trước, đánh dấu, lọc tệp, vị trí tệp, chia sẻ, khôi phục, nhật ký nhóm, lời mời, thông báo và quyền xem của thành viên. GitHub Actions chạy cùng bài thử bằng Chromium khi mở hoặc cập nhật pull request. Xem [các trình duyệt Playwright hỗ trợ](https://playwright.dev/python/docs/browsers).

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

## Tự kiểm tra giao diện với dữ liệu QA

- Mở **Kho lưu trữ** từ menu tài khoản góc trên phải. Trong kho cá nhân, tải một ảnh PNG, một PDF và một TXT có dấu tiếng Việt. Bấm tên từng tệp để xem. Kiểm tra ô chọn nằm sát cột tên, menu **Xem trước** vẫn hoạt động và Escape trả tiêu điểm về nút đã mở hộp thoại. Thử cả chế độ màn hình nhỏ.
- Có thể xem TXT, Markdown, CSV, LOG và JSON dưới dạng văn bản, tối đa 256 KiB. Hỗ trợ UTF-8 và UTF-16 có BOM. Dùng **Tải xuống** khi tệp quá lớn, định dạng chưa hỗ trợ hoặc trình duyệt thiếu trình xem PDF.
- Chọn nhiều mục rồi **Di chuyển** hoặc **Chuyển vào thùng rác**. Thử di chuyển hai mục vào thư mục có tệp trùng tên với một mục. Kiểm tra mục thành công được bỏ chọn, mục thất bại vẫn được chọn và có lý do hiển thị. Dùng tìm kiếm để chọn cả thư mục lẫn tệp con, rồi xác nhận tệp con đi cùng thư mục.
- Tải một tệp lớn hơn 8 MiB. Tạm ngắt rồi nối lại mạng trong cùng lượt tải; đối chiếu nội dung tải về. Thử bấm dừng và kiểm tra phần dung lượng đang giữ chỗ. Lượt tải có thể thử lại tối đa ba lần cho mỗi bước. Nếu mất mạng lâu hơn, kiểm tra danh sách sau khi kết nối lại trước khi chọn tải lại.
- Dùng quản trị viên QA kiểm tra **Quản trị → Tổng quan** và **Nhật ký quản trị**. Thử khóa rồi mở khóa một tài khoản mẫu, cấp gói thử và đổi giá một gói mẫu. Kiểm tra các mục trước/sau, chuyển trang khi có hơn 25 mục và thử mở nhật ký bằng tài khoản thường.

Xem [vận hành](../operations/OPERATIONS.md), [cấu trúc](../architecture/PROJECT-STRUCTURE.md), [kiểm chứng nguồn](../../artifacts/qa/deadcode-cleanup-2026-11-10.md).
