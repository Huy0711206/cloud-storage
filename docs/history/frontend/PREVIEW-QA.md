# Kiểm thử giao diện CloudBox Preview — cổng 8001

Ngày ghi nhận: 30/10/2026. Phạm vi: giao diện thiết kế thử nghiệm, dùng backend kiểm thử riêng.

## Build và kiểm thử tự động

- Kiểm tra TypeScript và build mặc định: đạt.
- Build Docker cuối của bản preview: đạt.
- Pytest: **31 kiểm thử đạt**; có một cảnh báo deprecation của httpx đã tồn tại trước đó.

## Kiểm tra trực tiếp trên Chromium

Dùng CUA kiểm tra các kích thước sau; không phát hiện tràn ngang ở tài liệu:

| Thiết bị | Kích thước |
|---|---|
| Desktop | 1440 × 1100 |
| Tablet | 768 × 1024 |
| Mobile | 390 × 844 |
| Mobile hẹp | 320 × 780 |

Các tương tác đã đạt:

- Đăng nhập sai hiển thị cảnh báo và đưa focus vào cảnh báo; đăng nhập thành công, đăng xuất cho cả người dùng và quản trị.
- Gói Tiêu chuẩn 12 tháng hiển thị tổng **690.000 ₫**; Escape đóng hộp thoại và trả focus về nút mở.
- Lọc đơn đã thanh toán rồi xuất CSV: đúng một dòng dữ liệu `QA-PAID-001`.
- Tìm kiếm không có kết quả: nút xuất CSV bị vô hiệu hóa; đặt lại tìm kiếm khôi phục danh sách.
- Mobile: chọn bộ lọc chờ thanh toán; ngăn điều hướng đóng sau khi chuyển mục.
- Chế độ tối được giữ sau khi tải lại trang.
- Lỗi lấy dung lượng hiển thị trạng thái lỗi; thử lại phục hồi thành công.
- Hộp trợ giúp hoạt động; liên kết bỏ qua điều hướng đưa focus vào nội dung chính. Mỗi trang kiểm tra có một vùng `main`; nút mở thanh bên có vùng bấm 44 px.
- Không ghi nhận lỗi JavaScript trong console ở các màn hình đã kiểm tra.

## Dữ liệu và giới hạn kiểm tra

Toàn bộ kiểm tra dùng SQLite tạm, Nextcloud giả và email giả. Không ghi vào database khách hàng thật, không thanh toán tiền thật và không đổi mật khẩu thật.

Ảnh chụp dùng dữ liệu QA, lưu trong workspace làm việc: `cloudbox-preview-desktop.jpg` và `cloudbox-preview-mobile-dark.jpg`.

Safari, Firefox và tùy chọn giảm chuyển động của hệ điều hành chưa được kiểm tra trực tiếp. CSS giảm chuyển động và nhánh dự phòng truy vấn mới được rà soát tĩnh; kết quả trên không thay thế kiểm tra trình đọc màn hình hoặc đánh giá WCAG đầy đủ.

## Xác nhận bản cuối

- Đã sửa thanh đầu trang tràn ở 320 px; kiểm tra lại trang chủ và dashboard không còn tràn ngang.
- Form đăng ký mobile có nhãn cho mọi trường; gửi trống giữ nguyên trang và focus vào họ tên.
- Đã xóa hai container QA, khôi phục 8001 tới backend portal thật.
- 8000 giữ nguyên asset bản ổn định; 8001 dùng asset preview. Hai health check đạt, Nextcloud trả 200 ở localhost:8080/login.
- Script khởi động đạt trên Windows PowerShell 5.1 và PowerShell 7 sau sửa kiểm tra URI của Nextcloud.
