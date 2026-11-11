> **Tài liệu lịch sử trước chuyển đổi native và xóa source ngày10/11/2026.** Các lệnh/đường dẫn ba dịch vụ bên dưới ghi nhận trạng thái cũ, không chạy trên dự án hiện hành. Xem [README](../../README.md) và [cây hiện hành](../architecture/PROJECT-STRUCTURE.md). Nội dung lịch sử được giữ nguyên bên dưới.

> Đường dẫn đã tổ chức lại ngày01/11/2026. Hướng dẫn hiện hành: README.md tại root; kết quả JSON và ảnh nằm artifacts/. Nội dung mô tả thời điểm QA trước đây vẫn là bằng chứng lịch sử, không mở lại các cổng cũ.

# Kiểm kê bảo toàn chức năng trước khi thay UI
Chuẩn chức năng là bản chính, không phải bản preview. Source/runtime đã khảo sát; cột kiểm thử là kế hoạch, kết quả thực nằm trong UNIFIED-QA.md. Không xem giữ source là bằng chứng đã thử tất cả luồng thực tế.

| Chức năng hiện tại | Nơi xử lý | UI hiện tại | Cách giữ trong bản mới | Kiểm thử |
|---|---|---|---|---|
| Public, bảng giá, gói | auth.py / GET / | React 8000/8001 | renderer preview + tokens mới; dữ liệu gói thật | public, responsive, theme, links |
| Đăng ký/xác thực/gửi lại | auth.py/register,verify,resend | native React forms | giữ form action/field/CSRF/session | Python auth tests, QA account riêng |
| Đăng nhập/logout/hết phiên | auth.py/login,logout / dependencies | React | giữ backend cookie theo BASE_URL | tests, browser QA public HTTPS |
| Dashboard/quota/storage | dashboard.py + Nextcloud API | React | preview overview, native sections | tests, QA quota, links public/local |
| Mật khẩu/tài khoản | auth.py/account/password | React forms | route/validation/quota logic không đổi | tests; không đổi mật khẩu thật |
| Orders/checkout/VNPay Return/IPN | billing.py, services billing/vnpay | React + redirects | không đổi nghiệp vụ/payment config | mock/sandbox tests; không giao dịch thật |
| Admin users/grant/lock/sync/plans/maintenance | admin.py | React admin | giữ toàn bộ actions/dialogs | tests + QA isolated data; không sửa user thật |
| Background expiry/sync/email | app/main.py/services | server | không đổi backend | Python tests |
| Duyệt/list/grid/upload/download/search/favorite | Nextcloud files/dav/search | 8080 native, 8081 subset | chính Nextcloud native + app theme | QA WebDAV/OCS + browser list/grid/search |
| Share/quyền/public/federated/email | files_sharing,sharing,sharebymail,federation | native dialogs/apps | giữ server + native UI, không gateway thay thế | QA own share + forbidden user; không email ngoài |
| Trash/restore/versions/locking/reminders | files_trashbin,files_versions,files_lock,files_reminders | native menu/sidebar/apps | giữ tất cả app enabled | QA trash/restore/version; source/app manifest compare |
| Preview PDF/photos/video/text/office | viewer,files_pdfviewer,photos,text,office | native viewer/apps | không đổi endpoints/renderers | QA text/image/PDF; office integration limitations report |
| Settings/profile/security/2FA/appmenu/activity/notifications/comments/tags/workflow | Nextcloud enabled app list | native | app theme không route/script replacement | compare enabled app list, browser settings, theme/a11y |
| API/WebDAV/OCS/Login Flow v2/quota/auth | Nextcloud server | native / remote clients | không proxy đổi hoặc DB mới | real QA API, unauth/forbidden, logout |
| Inbox/unread/search/filter/pagination/selection/tags | Mailpit /api/v1 | native Vue | source v1.32.0 native nguyên chức năng | QA SMTP local + list/search/tag/read/delete exact QA IDs |
| HTML/text/source/raw/headers/attachments/CID/calendar | Mailpit MessageItem + native API | Vue reader | giữ component/sanitization/iframe safety | QA multipart/CID/attachment/raw download |
| HTML check/link check/spam/screenshot/responsive preview | Mailpit native components/APIs | Vue tools | giữ source/options, không bật external service mới | local QA/check markup; không gọi link/email ngoài |
| Import/export/delete/read/manage/serverinfo/API docs | Mailpit native server/UI | Vue menus/modals | giữ nguyên; persist DB trước recreate | upstream tests + QA export/settings, no real deletions |
| WebSocket live/notifications/SMTP/relay/chaos settings | Mailpit server/config | native | same server/version/service; no relay enabled | live local QA, config flag compare; không gửi thật |
| Themes/settings/accessibility | mỗi app | native/pn en | radio thật portal/Mail, native NC controls | light/dark, keyboard, viewports, reduced motion/fallback evidence |

Nextcloud bật 51 app trước thay đổi; danh sách chính xác lưu trong backup runtime. Không coi đăng nhập riêng giữa portal và Nextcloud là kho riêng, không tự thêm SSO. Mailpit tính năng phụ thuộc cấu hình vốn có: relay/spam kiểm tra không được tự bật để làm demo.
