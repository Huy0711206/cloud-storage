# CloudBox Mail — kiểm thử giao diện 8026

Phạm vi: giao diện hộp thư React mới tại cổng 8026 và gateway tới Mailpit 1.32.0. Mẫu email xác thực và cấu hình SMTP của CloudBox không thuộc thay đổi này.

## Build và kiểm thử tự động

- Docker production build và kiểm tra TypeScript cuối cùng: đạt.
- JavaScript entry: 484,31 kB, gzip 169,68 kB; chunk khung đọc thư: 19,21 kB, gzip 7,09 kB.
- Pytest: **55 bài đạt**, còn một cảnh báo deprecation đã tồn tại trước đó.
- Bộ kiểm thử Node cho API đã lưu trong dự án: **10 bài đạt**.

## Kiểm tra trực tiếp trên Chromium

Không phát hiện tràn ngang ở tài liệu trong các kích thước đã kiểm tra:

| Thiết bị | Kích thước |
|---|---|
| Desktop | 1440 × 1000 |
| Tablet | 768 × 1024 |
| Mobile | 390 × 844 |
| Mobile hẹp | 320 × 780 |
| Mobile ngang | 844 × 390 |

Các tương tác và trạng thái đã xác minh:

- Mở thư HTML/văn bản, xem headers và nguồn thư; đánh dấu đã đọc/chưa đọc thành công trên dữ liệu QA.
- Mobile: nút có vùng chạm 44 px, quay lại từ thư về danh sách, đóng menu; chế độ tối được giữ sau khi tải lại.
- Thư mới xuất hiện mà không tải lại trang qua chu kỳ polling 10 giây.
- Với 25 thư, trang thứ hai hiển thị các dòng 21–25; nút trang trước bật và nút trang sau bị vô hiệu hóa.
- Tìm kiếm không có kết quả hiển thị trạng thái rỗng; xóa bộ lọc khôi phục danh sách.
- Xóa một thư QA thành công và có toast; mở lại ID đã xóa hiển thị trạng thái thư không còn tồn tại, nút quay lại đưa focus về danh sách.
- Dừng Mailpit QA tạo được trạng thái lỗi kết nối; khởi động lại và thử lại khôi phục dữ liệu.
- Escape đóng hộp trợ giúp: không còn dialog và focus trở về nút thông tin. Skip link đưa focus vào `mail-main`.
- Không có lỗi JavaScript trong log của tài liệu cuối cùng. Các thông báo CSP lịch sử trong thử nghiệm HTML độc hại có thể là kết quả chặn tài nguyên dự kiến, không được dùng để kết luận toàn bộ phiên không có log lỗi.

## Nội dung HTML, ảnh và tệp đính kèm

- Khung HTML dùng iframe với `sandbox` rỗng. Nội dung thử nghiệm sau xử lý không còn script, form, liên kết có `href` hoặc ảnh ngoài.
- Các cờ kiểm tra thực thi script/sự kiện trên trang cha vẫn là `null`.
- PNG mẫu đã được sửa CRC và kiểm tra lại. Ảnh CID được chuyển thành data URL; ảnh tải hoàn tất, `naturalWidth` bằng 1 như ảnh fixture.
- Đã thực hiện nhấp tải tệp đính kèm bằng giao diện native. Kiểm tra trực tiếp endpoint tải trả HTTP 200 và `Content-Disposition` đúng; tệp TXT có 187 byte và dữ liệu EML có `Return-Path`.
- Các kết quả tải ở trên xác minh thao tác và phản hồi máy chủ; không khẳng định tệp đã được lưu bền vững trong thư mục Downloads của trình duyệt.

## Dữ liệu và ảnh kiểm thử

Dùng container Mailpit tạm `cloudbox-mail-qa` trên mạng Docker, không mở thêm cổng host. Fixture `tests/mail_qa_seed.py` chỉ chấp nhận hostname QA này, không thể gửi vào service Mailpit thật bằng cách đổi biến môi trường sang `mailpit`.

Dữ liệu mẫu gồm thư văn bản có liên kết vô hiệu, thư HTML có ảnh CID/tệp đính kèm và thư HTML chứa script, sự kiện, form, iframe, CSS/ảnh ngoài để kiểm tra cô lập. Thư chỉ gửi tới Mailpit QA cục bộ, không gửi ra Internet; thao tác xóa/đánh dấu dùng dữ liệu QA riêng.

Ảnh dùng dữ liệu QA, lưu trong workspace làm việc: `cloudbox-mail-desktop.jpg` và `cloudbox-mail-mobile-dark.jpg`.

## Giới hạn

CSS và truy vấn media giảm chuyển động đã được rà soát; chưa giả lập tùy chọn reduced motion của hệ điều hành. Safari, Firefox và trình đọc màn hình chưa được kiểm tra trực tiếp. Các kết quả trên không thay thế đánh giá WCAG đầy đủ.

## Bàn giao runtime

**Đã xác nhận:** 8026 đã kết nối Mailpit thật; hai container QA đã được xóa. Hộp thư thật vẫn 0 thư / 0 chưa đọc. 8000, 8001, 8025, 8026 và Nextcloud 8080 đều hoạt động; các asset CloudBox ở 8000/8001 giữ nguyên. Script start-local.ps1 -NoBrowser chạy đạt trên Windows PowerShell.
