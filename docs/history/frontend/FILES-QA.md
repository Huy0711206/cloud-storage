# CloudBox Files 8081 — QA ngày 31/10/2026

## Phạm vi đã chạy

- Runtime: Nextcloud 35.0.2; service mới files-preview ở 127.0.0.1:8081.
- TypeScript và production build trong Docker đạt; lockfile giữ nguyên, không nâng thư viện.
- Toàn bộ Python: **76 passed**, gồm 55 test hiện có và 21 trường hợp mới của gateway Files. Một cảnh báo deprecation httpx/Starlette của môi trường, không gây thất bại.
- Client API hộp thư cũ: **10 passed**. Không sửa frontend/gateway hộp thư.
- Các test Python chạy trong container tạm --rm, source mount chỉ đọc, SQLite/FakeNC của bộ test; không dùng database thật để chạy unit test.

## Tích hợp Nextcloud thật với tài khoản QA riêng

Một tài khoản có UID bắt đầu cloudbox-files-qa- được tạo riêng, quota 100 MB, không phải tài khoản người dùng thật. Không gửi email QA. Các tệp skeleton Nextcloud chỉ thuộc tài khoản mới này.

Đã chạy qua HTTP gateway:

- Đăng nhập, UID thật, danh sách thư mục và quota (root trả permissions RGDNVCK).
- Tạo thư mục, thư mục tiếng Việt, upload raw bytes.
- Upload tên đã có trả 412; nội dung cũ không bị ghi đè.
- Yêu thích và REPORT trả đúng tệp đã đánh dấu.
- COPY, MOVE/đổi tên, DELETE vào thùng rác, MOVE khôi phục.
- Download sau khôi phục trả đúng từng byte nội dung đã upload.
- Text preview trả text/plain, danh sách chia sẻ OCS hoạt động.
- Logout làm GET list trả 401.
- Login Flow v2: start → pending=false → đăng nhập QA tại Nextcloud bằng HTTP với Origin/CSRF hợp lệ → grant QA → poll authenticated=true → list thành công → logout. Không bỏ qua CSRF hoặc sửa nội bộ xác thực để thử.

Lỗi phát hiện và sửa: Nextcloud 35 trả 412 khi Overwrite:F đi vào restore target ảo. Đã đọc mã RestoreFolder/Trashbin của bản đang chạy, thử bằng tệp QA và sửa riêng cờ restore; Nextcloud tự chọn tên duy nhất khi trùng. MOVE/COPY thông thường vẫn dùng Overwrite:F.

## Kiểm tra bằng trình duyệt thực

Dùng trình duyệt trong ứng dụng (Chromium/WebView). Không phải ảnh mockup.

- Đăng nhập QA, duyệt thư mục, URL path giữ sau tải lại.
- Tìm kiếm không có kết quả có hướng xóa tìm kiếm; quay lại danh sách đúng.
- Chuyển danh sách/lưới, light/dark mode.
- Tạo thư mục bằng bàn phím: auto-focus ô tên, Enter hoàn tất. Escape đóng dialog, focus về nút Tạo thư mục (đã đọc document.activeElement).
- Menu mobile mở bằng sheet, không tràn ngang.
- Chọn thư mục QA rỗng → xác nhận xóa → mục xuất hiện trong Thùng rác → xác nhận khôi phục → thư mục trở lại vị trí ban đầu.
- Xem trước PNG 1px: naturalWidth=1, naturalHeight=1, complete=true. Xem trước văn bản hiển thị đúng nội dung UTF-8.
- Upload qua file chooser: tệp TXT tiếng Việt tên dài đã xuất hiện trong danh sách. File chooser của công cụ mất nhiều thời gian mới trả kết quả; không suy diễn thời gian đó là benchmark upload của ứng dụng.
- URL thư mục QA không tồn tại hiển thị lỗi 404 có hướng làm mới và đường breadcrumb về thư mục hợp lệ.
- Khi service 8081 được recreate trong đợt triển khai, phiên trong RAM mất và UI quay về đăng nhập; đăng nhập lại trên bản cuối thành công.
- Console được kiểm tra: không có error/warn tại các lần quan sát.

Các kích thước đã kiểm tra:

| Kích thước | Kết quả |
|---|---|
| 1440 × 1000 | Desktop, sidebar và bảng tệp; không tràn ngang |
| 768 × 1024 | Tablet, điều hướng thu gọn; không tràn ngang |
| 390 × 844 | Mobile light/dark, menu, chi tiết, upload; không tràn ngang |
| 320 × 780 | Màn hình hẹp, tên tệp dài; không tràn ngang |
| 844 × 390 | Landscape; không tràn ngang |

Đã so sánh documentElement.scrollWidth với clientWidth/innerWidth. Chênh lệch 15px ở một số kích thước là thanh cuộn dọc. Mobile không render LiquidGlass, dùng fallback bề mặt thường.

Ảnh dữ liệu QA: cloudbox-files-desktop.png và cloudbox-files-mobile-dark.png trong workspace chat, không phải dữ liệu người dùng thật.

## Chưa kiểm tra / giới hạn

- Chưa trực tiếp kiểm tra Safari, Firefox, trình đọc màn hình, phóng chữ hệ điều hành hoặc emulation reduced-motion. Đã rà soát media query và fallback; không tuyên bố đạt WCAG đầy đủ.
- Chưa kiểm thử upload sát 2 GB, pause/resume, đứt mạng giữa tệp lớn hoặc tải đồng thời hàng nghìn tệp. UI/API có giới hạn, tiến độ, timeout và thông báo lỗi, nhưng các tình huống này chưa được thử bằng trình duyệt.
- Chưa thử bằng tài khoản thực có 2FA/SSO hoặc mounted external storage/read-only shares. Login Flow v2 giữ cơ chế của Nextcloud; kiểm thử hiện dùng tài khoản QA cục bộ.
- Chia sẻ nâng cao, PDF/Office/video preview, lịch sử phiên bản và tải cả thư mục ZIP mở qua Nextcloud gốc hoặc chưa hỗ trợ tại 8081, theo FILES-DESIGN.md.

Kết quả kiểm tra khởi động các cổng và dọn tài khoản QA cuối cùng được ghi tại PROGRESS.md sau khi hoàn tất.

## Bàn giao cuối

start-local.ps1 -NoBrowser kiểm tra thành công các cổng 8000/8001/8025/8026/8080/8081. Cả 8 service healthy; Nextcloud 8080 về localhost:8080/login đúng cổng. Mailpit giữ 0 thư/0 chưa đọc. Login Flow v2 đã chạy lại trên image cuối thành công. Tài khoản QA và tệp của nó đã xóa, xác minh tài khoản không còn tồn tại; credential QA cục bộ đã dọn, trang 8081 ở màn hình đăng nhập. git diff --check đạt.
