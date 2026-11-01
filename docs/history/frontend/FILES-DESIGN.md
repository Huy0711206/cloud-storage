# CloudBox Files — thiết kế và tích hợp 8081

Ngày: 31/10/2026. Phục vụ tại http://localhost:8081. Nextcloud gốc vẫn tại 8080.

## Thiết kế

Modern SaaS Dashboard, cùng nhận diện CloudBox 8001 nhưng ưu tiên danh sách tệp thay vì thẻ thống kê. Bộ gợi ý ui-ux-pro-max có palette/phông phù hợp; pattern landing “Product Demo” không phù hợp trình quản lý tệp nên không áp dụng.

| Vai trò | Light | Dark |
|---|---|---|
| Nền | #F5F7FB | #0D1422 |
| Bề mặt | #FFFFFF | #151F30 |
| Chữ | #13233A | #E9EFF9 |
| Chữ phụ | #586A82 | #ACBAD0 |
| Nhấn | #335CFF | #9AB7FF |
| Viền | #E0E6EF | #2D3B52 |

Font Plus Jakarta Sans Variable đã có, gồm subset tiếng Việt. Heading 27–32px; thông tin tệp và số liệu có phân cấp. Spacing 4/8px; radius 10px cho điều khiển, 12–16px cho bề mặt. Biểu tượng Lucide cùng dự án. Theme dùng semantic tokens, độc lập theo origin 8081 và key cloudbox-files-theme.

```text
Desktop: sidebar | header tài khoản
                 | breadcrumb + tên thư mục + tạo/tải lên
                 | tìm kiếm + kiểu xem
                 | danh sách/lưới + trạng thái
                 | footer
                 | chi tiết mở bằng sheet bên phải

Tablet/mobile: header + menu mở sidebar bằng sheet
               breadcrumb + tiêu đề
               tạo thư mục / tải lên
               tìm kiếm / kiểu xem / sắp xếp
               danh sách thích ứng hoặc lưới hai cột
```

Liquid Glass 1.1.1 chỉ dùng ở cụm chọn danh sách/lưới trên màn hình rộng có con trỏ chính xác, không bật reduced motion. Standard mode, displacement thấp, elasticity=0; mobile/reduced-motion dùng bề mặt thường. Không hiệu ứng kính trên tên tệp, biểu mẫu hoặc nội dung.

## Kiến trúc

Browser → 127.0.0.1:8081 → files-preview (React + FastAPI gateway) → http://nextcloud trong Docker.

Gateway chỉ có NEXTCLOUD_UPSTREAM và NEXTCLOUD_PUBLIC. Không nhận .env hoặc credential quản trị, không có database/volume riêng. Không sửa lõi Nextcloud, không chèn CSS vào 8080 và không đưa HTML Nextcloud qua proxy thay giao diện.

Build riêng: vite.files.config.ts → dist-files → static/files trong image Dockerfile.files-preview. Dùng chung dependencies/lockfile và component shadcn hiện có, giữ React 19.3.1/Tailwind 4.3.3 theo lockfile hiện tại. Các bundle đang phục vụ ở 8000/8001/8026 không được rebuild.

## Đăng nhập và phiên

1. GET /api/files/session tạo phiên mờ, lấy CSRF.
2. POST /api/files/login/start gọi Nextcloud Login Flow v2. Trình duyệt mở trang cấp quyền ở 8080.
3. POST /api/files/login/poll giữ poll token phía server; nhận app password phía server sau khi người dùng cấp quyền. API trình duyệt chỉ nhận authenticated, không nhận app password.
4. Dùng OCS cloud/user để lấy UID thật thay vì coi email đăng nhập là tên đường dẫn WebDAV.
5. Phiên authenticated hết hạn sau 8 giờ. Credential chỉ ở RAM của một process, không ghi cookie/localStorage/file/database. Chạy đúng một worker.
6. Đăng xuất loại bỏ phiên và thử thu hồi app password do Login Flow tạo. Bộ dọn chạy mỗi phút, và khi tắt dịch vụ bình thường cũng thử thu hồi các quyền còn giữ.

Mật khẩu ứng dụng do người dùng nhập là phương án thay thế khi không thể mở luồng cấp quyền; gateway không thu hồi credential dùng chung do người dùng tự cung cấp. Không có biểu mẫu yêu cầu mật khẩu quản trị. Khi container bị kill đột ngột hoặc mất kết nối lúc thu hồi, app password có thể còn xuất hiện trong Nextcloud → Bảo mật; người dùng có thể thu hồi tại đó. Sau restart, phiên 8081 mất và cần đăng nhập lại.

Cookie tên riêng cloudbox_files_session, HttpOnly, SameSite=Strict, Path=/api/files; HTTPS dùng Secure. Khác cổng không tách cookie theo chuẩn trình duyệt, vì vậy gateway không dùng cookie của portal/Nextcloud và không chuyển cookie upstream. Mọi POST/PUT kiểm tra Origin chính xác gồm cổng và CSRF, không mở CORS. 8081 logout không đăng xuất phiên web 8080.

## Chức năng và giới hạn rõ ràng

- WebDAV: duyệt, breadcrumb, tải lên streaming tối đa 2 GB/tệp, tải xuống tệp streaming, MKCOL, MOVE/COPY, DELETE vào thùng rác, PROPPATCH/REPORT yêu thích, thùng rác/khôi phục.
- Không ghi đè tệp khi upload (If-None-Match: *), di chuyển/sao chép (Overwrite: F). Tên trùng có lỗi hướng dẫn chọn tên khác.
- Nextcloud 35 cần Overwrite: T cho đích ảo restore. Đã kiểm tra mã RestoreFolder/Trashbin đang chạy: restore chọn tên duy nhất khi trùng, không dùng cờ này cho MOVE/COPY thông thường.
- UI kiểm tra quyền từ oc:permissions để khóa tạo/đổi tên/di chuyển/xóa; Nextcloud vẫn là nơi thực thi quyền cuối cùng.
- Chọn nhiều: sao chép/di chuyển/xóa/khôi phục theo từng mục, báo số mục đã hoàn thành khi có lỗi; không gửi lại các mục đã thành công khi thử lại.
- Tìm kiếm lọc tên trong danh sách hiện tại, không phải tìm toàn bộ kho. Sắp xếp theo tên, dung lượng hoặc ngày sửa; thư mục đứng trước. Không giả danh sách này là lịch sử “Gần đây”.
- Xem trước: raster PNG/JPEG/WebP/GIF tối đa 20 MB; văn bản TXT/MD/CSV/LOG/JSON tối đa 2 MB. Văn bản hiển thị như text, không thực thi HTML/Markdown/script; SVG/HTML/PDF/Office/video chưa có trình xem riêng. Không tải cả thư mục thành ZIP trong UI mới.
- Xem các chia sẻ hiện có do API trả về. Tạo/sửa chia sẻ, lịch sử phiên bản và tiện ích khác mở Nextcloud gốc; không có nút tạo chia sẻ giả.
- Không có xóa vĩnh viễn/xóa toàn bộ thùng rác ở gateway. Không có endpoint proxy tùy ý. Root không được phép mutation; đường dẫn traversal/control characters bị từ chối. Phản hồi WebDAV 207 có lỗi con không được báo thành công.

## Tài liệu đối chiếu

- https://docs.nextcloud.com/server/stable/developer_manual/client_apis/LoginFlow/index.html
- https://docs.nextcloud.com/server/stable/developer_manual/client_apis/WebDAV/basic.html
- https://docs.nextcloud.com/server/stable/developer_manual/client_apis/WebDAV/trashbin.html
- https://docs.nextcloud.com/server/stable/developer_manual/client_apis/OCS/ocs-share-api.html

Tại thời điểm khảo sát, tài liệu trả Nextcloud 35 và runtime là 35.0.2 (35.0.2.2). Kết quả QA cụ thể nằm trong FILES-QA.md.
