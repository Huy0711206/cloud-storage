# CloudBox — thiết kế thử ở cổng 8001

## Định hướng đã đề xuất trước khi triển khai

Một không gian lưu trữ rõ ràng, nhẹ và có thứ bậc. Dữ liệu thật quyết định nội dung: dung lượng, gói, đơn hàng, tình trạng tài khoản. Không thêm biểu đồ hoặc danh sách tệp giả. Các thao tác tệp vẫn mở kho Nextcloud hiện có.

## Design system

| Lớp | Token | Sáng | Tối |
|---|---|---|---|
| Primitive | Cloud / Ink / Cobalt | `#F5F7FB` / `#13233A` / `#335CFF` | Giá trị nền tảng không đổi |
| Semantic | background / foreground | `#F5F7FB` / `#13233A` | `#0D1422` / `#E9EFF9` |
| Semantic | card / muted text | `#FFFFFF` / `#5B6B82` | `#151F30` / `#A9B8CE` |
| Semantic | primary / on-primary | `#335CFF` / trắng | `#9AB7FF` / `#14244A` |
| Component | sidebar active | accent + cobalt marker | accent + primary marker |
| Component | card | radius 18px, padding 26–28px | cùng kích thước |
| Component | controls | radius 10px, cao tối thiểu 44px | cùng kích thước |

Font Plus Jakarta Sans Variable, tự lưu trong bản build, hỗ trợ tiếng Việt. Nội dung chính 14–16px; thông tin phụ 12–13px; tiêu đề trang 26–30px; số dung lượng 35–38px, chữ số tabular. Khoảng cách theo nhịp 4/8px; ưu tiên 24–32px giữa các vùng và 12–16px trong nhóm thao tác.

## Bố cục

- Desktop: sidebar cố định, thanh điều hướng trên, nội dung chính hai cột. Cột lớn: dung lượng với thanh tiến trình, truy cập nhanh, đơn hàng gần đây. Cột nhỏ: gói hiện tại, trạng thái tài khoản và giải thích thanh toán.
- Tablet: nội dung chính chuyển một cột, hai thẻ phụ nằm cạnh nhau nếu đủ chỗ.
- Mobile: sidebar thành drawer có nhãn, gói và tài khoản xếp dọc. Bảng có vùng cuộn riêng, bộ lọc đơn hàng dùng select; thao tác chạm tối thiểu 44px.
- Trang công khai: phần giới thiệu và hình kho được dựng bằng CSS/Lucide, khả năng hệ thống, bảng giá từ dữ liệu backend, lời mời đăng ký. Đăng nhập/đăng ký giữ hợp đồng form hiện có.

Liquid Glass chỉ dùng cho cụm công cụ trên desktop với con trỏ chính xác. Có vùng chứa kích thước xác định, giữ transform do thư viện quản lý. Touch/mobile và reduced motion dùng bề mặt thường. Nội dung và form luôn dùng nền đặc. Cần kiểm tra thêm Safari/Firefox trên thiết bị thật vì hiệu ứng SVG displacement phụ thuộc trình duyệt.

## Trạng thái và khả năng truy cập

- Lazy loading: skeleton có `role=status`; native form có trạng thái gửi và ngăn gửi lặp.
- Empty: giải thích đơn hàng chưa có, liên kết tới gói dịch vụ.
- Error: lỗi dung lượng có nút thử lại; lỗi form có tóm tắt, liên kết trường và nhãn; banner ngoại tuyến.
- Radix/shadcn quản lý dialog, dropdown, drawer, focus trap, Escape và trả focus. Giữ skip link, tên truy cập của nút icon, bảng có caption và biểu tượng kèm chữ trạng thái.
- Animation xuất hiện 220ms và hover nhẹ; tôn trọng `prefers-reduced-motion`. Không dùng hiệu ứng nhấp nháy hoặc chuyển động liên tục trong dashboard.

## Cô lập triển khai

`VITE_UI_VARIANT=preview` chọn `src/preview/PreviewApp.tsx`. Build mặc định vẫn dùng App ổn định. Dịch vụ `portal-preview` ở 8001 thay asset giao diện và chuyển tiếp nghiệp vụ về portal 8000. Cả hai chia sẻ tài khoản, phiên và dữ liệu thật; không phải môi trường dữ liệu độc lập. Không chạy thêm backend nghiệp vụ hoặc maintenance job. Liên kết email/thanh toán dùng BASE_URL cấu hình ở backend.

## Kiểm thử

TypeScript + production build; bộ kiểm thử backend/gateway; browser desktop/tablet/mobile với tài khoản mẫu trong SQLite tạm, kho/email giả, không có port host mới. Kiểm tra đăng nhập/lỗi form, điều hướng, bảng giá/thời hạn/dialog, bộ lọc/CSV, theme, menu mobile, lỗi dung lượng/phục hồi. Sau QA khôi phục 8001 về backend thật và xóa container QA.
