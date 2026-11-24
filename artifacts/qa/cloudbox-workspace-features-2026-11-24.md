# Kiểm thử kho tệp và lệnh phát hành ngày 24/11/2026

## Tính năng kho

- Kho cá nhân có đánh dấu tệp và thư mục theo tài khoản. Đã đánh dấu mở đúng thư mục. Sau khi đổi tên hoặc di chuyển, dấu gắn với mã mục. Khi đưa vào thùng rác, mục được ẩn và xuất hiện lại khi khôi phục.
- Tìm kiếm theo tên trong kho cá nhân. Bộ lọc loại tệp, ngày chỉnh sửa và kích thước dùng truy vấn kho hiện có. Kết quả được phân trang và có đường dẫn đến thư mục chứa mục.
- API kho nhóm dùng lại trình xem trước và kiểm tra quyền kho nhóm. Thành viên chỉ xem được tệp trong đúng nhóm đang tham gia. Người có quyền chỉ đọc vẫn xem trước được. Sau khi gỡ thành viên, API xem trước và nhật ký từ chối tài khoản đó.
- Nhật ký bắt đầu ghi từ khi tính năng được cài. Tạo thư mục, tải tệp, cập nhật, đổi tên, di chuyển, đưa vào thùng rác, khôi phục và khôi phục phiên bản được ghi trong cùng giao dịch. Thử gửi lại yêu cầu hoàn tất tải tệp chỉ tạo một sự kiện.
- Chuông thông báo hiển thị lời mời đang chờ, tệp vừa nhận qua yêu cầu nhận tệp và gói còn tối đa 7 ngày. Trạng thái đã đọc gắn riêng với tài khoản. Kiểm thử xác nhận lời mời đã thu hồi được ẩn và thao tác hoàn tất gửi lặp không tạo thông báo trùng.

## Kết quả

- Lệnh kiểm tra mặc định đạt 209 bài backend, 7 bài Node, kiểm tra TypeScript và build Vite. Có 9 lượt bỏ qua trong cấu hình mặc định.
- Tám kiểm thử PostgreSQL chạy riêng đạt trên database Docker thử nghiệm. Trong database thử nâng cấp khác, image mới tạo thêm ba bảng và vẫn đọc đúng mật khẩu đã băm, gói, đơn hàng và mục thư mục mẫu. Image trước tiếp tục đọc được dữ liệu mẫu sau khi thêm bảng.
- Playwright chạy qua Microsoft Edge với cửa sổ 1280 px và thành viên ở 390 px. Các luồng đăng nhập, tải lên, xem trước, đánh dấu, tìm kiếm, chia sẻ, thùng rác, nhật ký nhóm, lời mời và xem tệp bằng quyền chỉ đọc đều đạt trên image cuối.
- Lệnh PowerShell phát hành chạy hoàn tất ở chế độ PrepareOnly. Script EC2 đạt kiểm tra cú pháp và mô phỏng cập nhật thành công, thất bại rồi phục hồi image trước. Kiểm thử chạy trên laptop với dữ liệu QA và EC2 giả lập.

## Phát hành AWS Academy

- Phiên AWS Academy đã được mở để cập nhật máy EC2 cloudbox-app-01. Lệnh release-aws.ps1 chạy 209 bài backend, 7 bài Node, kiểm tra TypeScript và Playwright trên image Docker dự định phát hành.
- Bản release-20261124075455-4332fea5 được đối chiếu SHA-256 trước khi thay riêng Portal. Kiểm tra xác nhận các container PostgreSQL và tunnel cùng volume tệp được giữ qua lần cập nhật.
- Trên EC2, PostgreSQL có đủ ba bảng mới sau khi Portal khởi động và các bảng tài khoản, gói, đơn hàng và kho vẫn đọc được metadata. Tên miền HTTPS phục vụ đúng giao diện mới, health/readiness đều đạt và API thông báo yêu cầu đăng nhập.
- Các thao tác sau đăng nhập được thử với tài khoản mẫu trong QA.
