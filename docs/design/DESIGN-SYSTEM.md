> Đường dẫn đã tổ chức lại ngày01/11/2026. Hướng dẫn hiện hành: README.md tại root; kết quả JSON và ảnh nằm artifacts/. Nội dung mô tả thời điểm QA trước đây vẫn là bằng chứng lịch sử, không mở lại các cổng cũ.

# CloudBox — thiết kế và kiến trúc hợp nhất
Ngày khảo sát: 31/10/2026. Đây là phương án được trình bày trước khi thay ứng dụng.

## Hiện trạng và lựa chọn
8000 là FastAPI + React chính. 8001 là React preview chuyển tiếp cùng backend, không DB riêng. 8080 là Nextcloud 35.0.2 đầy đủ; 8081 là React Files qua Login Flow v2/WebDAV/OCS, không DB riêng nhưng thiếu nhiều UI native. 8025 là Mailpit v1.32.0 đầy đủ; 8026 là React/gateway chỉ một phần API. Có hai Quick Tunnel tới portal:8000 và nextcloud:80, không tunnel mail.

8000 dùng lại renderer preview đã kiểm thử và thay design system trên toàn bộ public/auth/dashboard/admin. Nextcloud dùng app cloudbox_theme qua public bootstrap event, giữ native layout/apps/session/API/WebDAV/OCS. Mailpit build đúng source v1.32.0 giữ Vue và toàn bộ native components/backend. Không promote gateway thiếu chức năng lên cổng chính. Không tạo dữ liệu/tài khoản riêng hay sửa lõi Nextcloud.

## Design system
Light: ground #FCFCFD, muted #F3F4F6, panel #FFFFFF, ink #16191F, secondary #454C58, rule #DDE0E6, accent #074CE0, on-accent #FFFFFF. Dark: ground #11141A, muted #202630, panel #181D26, ink #F4F6FB, secondary #BAC3D2, rule #364050, accent #8EB1FF, on-accent #12213C. Semantic source: packages/design-system/tokens.css.

Font mẫu Host Grotesk/Instrument Sans thiếu nhiều glyph Việt (đã kiểm cmap). Thay rõ ràng bằng Be Vietnam Pro cho toàn bộ chữ/heading; font tự host, OFL kèm theo. Body 16, interface 15, small 14, metadata 13, label 12, leading 1.6. Spacing 4/8, grid 24, panel radius 12, viền 1, focus 3, mục tiêu thao tác 44px trên cảm ứng. Motion 160ms ease-out, không animation trang trí liên tục.

Kính chỉ ở radio theme/toolbar thích hợp, inset highlight nhẹ, blur fallback nền đặc. Không copy asset khúc xạ không rõ giấy phép, không contrast toàn trang hay chặn pointer. Radio có legend, nhãn, tên nhóm riêng, phím mũi tên/Tab. Light/dark/system: portal lưu preference local; Mailpit dùng mp-theme native; Nextcloud giữ Appearance native + high contrast/dyslexia/reduced-motion. Không endpoint/cookie theme chung. Chưa thêm Dim cho toàn hệ thống; giữ deep-dark vốn có của Mailpit trong Settings.

## Bố cục và minh họa
CloudBox: desktop sidebar 248px, header 76px, content tối đa 1440; overview dung lượng/đơn hàng và cột gói/tài khoản; trang khác giữ native forms. Public hero 1.45:1 theo nội dung hiện có, không số liệu giả. Tablet một cột overview khi cần; mobile sidebar sheet, forms full width.
Nextcloud: native navigation/search/app menu/list/grid/sidebar được giữ; bề mặt sáng rõ, font và màu chung, panel 12px, header 64/56px. Không thay bằng React hoặc hứa bố cục tùy ý tương thích tất cả app. High contrast và font dyslexia được tôn trọng.
Mail: native sidebar/danh sách/reader, header sáng thay thanh tối, panel viền rõ, theme radio ở footer sidebar/offcanvas, menu chức năng và iframe nội dung thư nguyên gốc.
Mockup tham khảo: artifacts/design/mockup.html (không phải ứng dụng hay số liệu thật); ảnh QA trước/sau ghi trong UNIFIED-QA.md.

## Chuyển đổi / khôi phục
Sao lưu từng tệp thay đổi, fingerprint config và image trước; không ghi secret vào Git. Mailpit hiện ở /tmp, cần dừng có kiểm soát, sao lưu SQLite gốc rồi nhập vào mailpit_data trước recreate. Giữ image cũ và volume chính.
Build/type/test trước, chuyển lần lượt 8000/8080/8025, kiểm tra thực tế rồi ngừng đúng ba container preview. Giữ tuyến tunnel và trạng thái .online, không hardcode hostname. Các cổng cuối 8000/8080/8025; DB/Redis/SMTP vẫn nội bộ. Rollback cụ thể được ghi sau khi thực hiện. Không down -v.
