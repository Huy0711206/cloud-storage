# CloudBox Mail — thiết kế cổng 8026

## Phương án đã đề xuất trước khi code

Giữ Mailpit 1.32.0 tại 8025 và SMTP hiện có. Giao diện React riêng tại 8026 đọc cùng API qua gateway cố định. Không sửa mẫu email, không thêm kho thư hoặc database nghiệp vụ. Khi mở thư, API Mailpit đánh dấu đã đọc; đánh dấu/xóa tác động lên cùng hộp thư ở cả 8025 và 8026.

Nguồn xác minh API: Swagger của phiên bản đang chạy tại `http://localhost:8025/api/v1/swagger.json`; tài liệu bộ lọc chính thức `https://mailpit.axllent.org/docs/usage/search-filters/`. Cập nhật danh sách bằng REST mỗi 10 giây khi tab hiển thị; không tự mở chi tiết thư khi poll. API send/relay/release không được gateway cho phép.

## Design system

| Vai trò | Sáng | Tối |
|---|---|---|
| Nền | #F5F7FB | #0D1422 |
| Vùng đọc và danh sách | #FFFFFF | #151F30 |
| Chữ chính | #13233A | #E9EFF9 |
| Chữ phụ | #5B6B82 | #A9B8CE |
| Mục chọn / hành động | #335CFF | #9AB7FF |
| Viền | #E0E6EF | #2D3B52 |

Plus Jakarta Sans Variable tự lưu trong build. Tiêu đề 22–24px, nội dung đọc 14–16px, nhãn 12–13px. Nhịp khoảng cách 8px, phân tách theo vùng thay vì chia mọi nội dung thành thẻ. Nút cao tối thiểu 44px, focus 3px. Thư chưa đọc có chữ đậm, dấu chấm và nhãn truy cập; không dựa riêng vào màu.

Skill ui-ux-pro-max gợi ý Flat Design phù hợp công cụ email. Phần gợi ý landing/product demo không phù hợp inbox nên không áp dụng. Giữ font và nhận diện của CloudBox thay vì thêm font/phong cách mới. Liquid Glass chỉ là cụm công cụ nhỏ, có fallback ở màn hình hẹp, pointer thô, reduced motion hoặc trình duyệt ngoài Chromium; thư luôn nằm trên nền đặc.

## Bố cục

Desktop: `[Điều hướng 222px] [Danh sách 370px] [Nội dung co giãn]`.
Tablet: `[Menu thu gọn]`, phía dưới `[Danh sách] [Nội dung]`.
Mobile: `[Danh sách]` → chọn thư → `[Quay lại + Nội dung]`.

Danh sách gồm tên gửi, thời gian, tiêu đề, đoạn trích, người nhận và số tệp đính kèm. Thanh tìm kiếm và phân trang luôn có nhãn. Khung đọc có HTML, văn bản, headers, nguồn thư và tải tệp/EML.

## Trạng thái và truy cập

Skeleton khi tải, Empty khi trống/không kết quả/chưa chọn, lỗi kết nối có thử lại, xử lý thư không còn tồn tại. Trạng thái chờ khóa thao tác lặp. Dialog xóa nêu rõ phạm vi dùng chung và không hoàn tác; thao tác QA chỉ trên hộp thư tạm. Skip link, keyboard, Escape và trả focus. Theme lưu tại origin 8026, không sửa giao diện đang chạy ở 8000/8001.

Nội dung HTML đi qua allowlist trong template trơ, iframe opaque sandbox và CSP. Không thực thi script, form, điều hướng liên kết hay tải tài nguyên ngoài. Ảnh CID raster lấy từ endpoint part của Mailpit thành data URL; nguồn thư và headers được render như văn bản escaped. CSS email không ảnh hưởng ứng dụng.

## Kiểm tra

TypeScript và build riêng `vite.mail.config.ts` ra `dist-mail`. Kiểm thử gateway với mock transport; QA browser bằng Mailpit tạm không mở cổng host bổ sung. Dữ liệu QA gồm thư văn bản, HTML/CID/tệp, HTML có nội dung cần chặn. Khôi phục 8026 về Mailpit thật, dọn container QA và xác minh các cổng cũ trước bàn giao.
