# Kiểm thử mở kho và xem tệp trực tiếp

- Dùng tài khoản giả trên SQLite và tệp mẫu. **Kho lưu trữ** trong menu tài khoản đưa quản trị viên tới `/files#storage` và thành viên tới `/dashboard#storage`.
- Bấm tên PNG để mở ảnh. Nhấn Escape để đóng và trở về tiêu điểm trên tên tệp. Bấm tên TXT bằng Enter để đọc chữ tiếng Việt, giữ dấu, khoảng trắng và xuống dòng. Thao tác **Xem trước** trong menu ba chấm vẫn mở nội dung. Thư mục mở danh sách bên trong và tệp BIN mở hộp thông tin có thể tải xuống.
- Cột chọn rộng 44 px trên màn hình 1280 px và 36 px trên màn hình 390 px. Khoảng cách từ mép ô chọn đến biểu tượng tệp là 16 px ở cả hai kích thước. Bảng thử vừa khung và hộp thoại văn bản vừa viewport 390 px.
- 11 bài kiểm thử API xem trước đạt với ảnh, PDF, văn bản, mã hóa, kích thước và quyền truy cập. TypeScript và build Vite đạt với lockfile hiện có.

Giới hạn xem chữ là 256 KiB cho TXT, Markdown, CSV, LOG và JSON mã hóa UTF-8 hoặc UTF-16 có BOM. Đợt kiểm tra này dùng bản QA trên laptop.

## Phát hành AWS Academy

- Gói Docker linux/amd64 vượt qua kiểm tra trên SQLite, gồm phản hồi của Portal, quyền xem trước và nội dung văn bản Unicode.
- Đối chiếu SHA-256 trước khi nạp image vào EC2. Chỉ tạo lại container Portal. ID container PostgreSQL và Tunnel, cùng volume kho gắn vào Portal, khớp trước và sau triển khai.
- HTTP nội bộ kiểm tra Portal và tunnel đều đạt. HTTPS xác nhận /healthz và /readyz trả về status ok. Trang chủ dùng main-BMJffZjN.js và nạp gói giao diện có mục menu kho, xem trước văn bản và cột chọn tệp.
- Các tương tác sau đăng nhập được thử với tài khoản giả và tệp mẫu trên môi trường QA.
