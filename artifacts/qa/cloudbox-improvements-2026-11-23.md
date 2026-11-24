# Kiểm thử cải tiến CloudBox ngày 23/11/2026

Đã chạy `scripts/development/check.ps1` trên bản làm việc riêng với Python 3.12, SQLite và tệp tạm. Backend đạt 201 bài, bỏ qua 9 bài. Tám bài cần PostgreSQL đã chạy riêng trên PostgreSQL 16 dùng một lần và đều đạt. Bài còn lại cần quyền tạo liên kết tệp Windows. Bảy bài Node đạt. TypeScript và build Vite đạt. Bộ kiểm thử báo cảnh báo tương thích Starlette và Vite đã có từ trước.

| Hạng mục | Bằng chứng |
|---|---|
| Kiểm tra phát hành | Lệnh PowerShell chạy hết các bước. Bộ mặc định thu thập `test_frontend.py`. Chạy workflow trên GitHub sẽ cần đẩy mã và mở pull request. |
| Chẩn đoán | Test kiểm trạng thái PostgreSQL, ổ lưu trữ và ngân sách trong môi trường QA. Trình duyệt hiển thị cả hai bảng dung lượng trên Tổng quan quản trị. Trạng thái Tunnel được kiểm qua phép thử hiện có của EC2 khi vận hành. |
| Gói trả phí | Test xác nhận gói miễn phí, gói trả phí còn hạn, đã hết hạn và thời điểm đúng bằng ngày hết hạn. |
| Xem trước | Test quyền truy cập, nhận dạng nội dung, tệp trong thùng rác và cách tải xuống. Trình duyệt nạp được ảnh thật, Escape trả tiêu điểm về nút thao tác và hộp PDF vừa khung 390 px với tùy chọn tải xuống. Việc hiển thị từng trang PDF phụ thuộc vào trình xem của trình duyệt. |
| Thao tác nhiều tệp | Test giữ tệp con đi cùng thư mục, từ chối mục ngoài quyền, xử lý mục đã chuyển vào thùng rác, xung đột tên và khôi phục. Trình duyệt ghi nhận một mục di chuyển thành công, một mục trùng tên còn được chọn, và hai mục đã chuyển hiện trong Thùng rác. |
| Thử lại tải lên | Test mô phỏng mất phản hồi trước và sau khi máy chủ ghi khối, thử lại hoàn tất, dừng khi hết lượt, hủy và lỗi vĩnh viễn. Test backend đối chiếu dữ liệu sau tải. |
| Nhật ký quản trị | Test ba loại thao tác, phân trang, quyền truy cập và hoàn tác giao dịch lỗi. Kiểm thêm bảng trên SQLite và PostgreSQL 16 đã có tài khoản mẫu, xác nhận tài khoản vẫn tồn tại. Trình duyệt hiển thị mục khóa tài khoản QA với trạng thái trước/sau. |

Các bước thử tay nằm trong [hướng dẫn phát triển](../../docs/development/DEVELOPMENT.md). Khi phát hành lên AWS, làm theo [quy trình xác nhận và yêu cầu schema](../../docs/operations/AWS-ACADEMY.md). Lượt này kiểm thử bằng dữ liệu riêng trên laptop.

## Xác nhận trên AWS

Docker image `cloudbox-portal:improvements-20261123` được nạp từ gói đã khớp SHA-256. Portal báo healthy và kết nối PostgreSQL đọc được bảng `admin_audit_entries`. Container PostgreSQL, Tunnel và volume kho vẫn dùng định danh đã ghi nhận trước khi thay Portal.

HTTPS `/healthz` và `/readyz` trả trạng thái `ok`. Trang chủ tham chiếu `main-CnMROxa4.js`. Tài nguyên giao diện chính, kho và quản trị của bản mới đều tải HTTP 200. `/admin/audit` chuyển hướng về đăng nhập khi chưa có phiên.
