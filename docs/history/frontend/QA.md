# Kiểm thử giao diện CloudBox

- TypeScript và Vite production build: đạt trên Windows và trong Docker Linux.
- Backend + public UI bootstrap: 19/19 kiểm thử đạt, dùng SQLite tạm và Nextcloud giả.
- Desktop 1440×1000, tablet 768×1024, mobile 375×812: các trang kiểm tra không tràn ngang.
- Đăng nhập người dùng và quản trị; đăng xuất từ menu tài khoản: đạt.
- Gói 12 tháng: Cơ bản 250.000 ₫, Tiêu chuẩn 690.000 ₫, Cao cấp 1.990.000 ₫; hộp xác nhận hiển thị đúng tổng.
- Hộp thoại đóng bằng Escape, trả focus về nút mở; menu mobile mở/đóng và chuyển mục: đạt.
- Dark mode được lưu sau khi tải lại; light mode và typography tiếng Việt: đã xem trực tiếp.
- Đăng ký với hai mật khẩu khác nhau: không gửi biểu mẫu, hiển thị lỗi gần trường, focus vào phần tổng hợp lỗi.
- Skip link đưa focus đến nội dung và giữ nguyên mục đang xem.
- Trang chưa có đơn hàng, quản trị tìm không có kết quả, trường hạn mức/giá gói miễn phí: đạt.
- Cấp gói: chọn gói trả phí mở trường thời hạn; hủy không ghi dữ liệu.
- Các trang thật /, /login, /register trả 200; xác thực sai token trả 400; trang không tồn tại trả 404. Mỗi trang đều có bootstrap JSON và tài nguyên React trả 200.
- Không thấy lỗi JavaScript trong các màn hình đã kiểm tra.

## Phạm vi

Đợt kiểm thử giao diện trước đây dùng máy chủ tạm cổng 8002 (đã dừng và bỏ helper chạy thử), tài khoản mẫu và dữ liệu tạm; không đổi tài khoản thật, không thanh toán tiền thật. Luồng ký nhận VNPay và đồng bộ Nextcloud được kiểm tra bằng bộ backend hiện có. Giao diện quản lý tệp Nextcloud tiếp tục chạy riêng; đợt này thiết kế lại cổng CloudBox. Các kiểm tra bàn phím và tương phản cơ bản không thay thế đánh giá WCAG đầy đủ bằng trình đọc màn hình.

## Cổng sau khi sửa khởi động

CloudBox chính: http://localhost:8000. Địa chỉ dự phòng: http://localhost:8001. Hai cổng cùng phục vụ một portal. Không còn máy chủ kiểm thử cổng 8002 trong quy trình chạy.
