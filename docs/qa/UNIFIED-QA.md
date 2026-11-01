> Đường dẫn đã tổ chức lại ngày01/11/2026. Hướng dẫn hiện hành: README.md tại root; kết quả JSON và ảnh nằm artifacts/. Nội dung mô tả thời điểm QA trước đây vẫn là bằng chứng lịch sử, không mở lại các cổng cũ.

# QA hợp nhất CloudBox — 31/10/2026

> **Cập nhật 01/11/2026:** Kết luận phiên bản404 trước đây đã được hiệu chỉnh: bài thử gọi endpoint archive cho bản hiện tại; native dùng files DAV và tải đúng byte. Viewer đã có bản vá hai fallback Sidebar (17 test); app integrity sẽ báo đúng loader/module đã vá, core kiểm riêng. Lỗi MutationObserver tái hiện trên trang iframe không có Mailpit/JavaScript, thuộc lớp môi trường trình duyệt chưa xác định module cụ thể. Xem [chẩn đoán mới](DIAGNOSTICS-2026-11-01.md) và DIAGNOSTICS-FINAL.json. Các ghi nhận cũ phía dưới là lịch sử trước chẩn đoán.


Phạm vi: UI chính 8000 / Nextcloud native 8080 / Mailpit native 8025. Không đổi nghiệp vụ, không dùng tài khoản thật để thử, không gửi email ra ngoài hoặc giao dịch tiền thật. Tài khoản/thư/tệp QA tạm dùng miền example.invalid; dọn riêng sau thử.

## Bằng chứng đạt

- TypeScript và production build CloudBox đạt với pnpm/lockfile hiện có. Không nâng dependency frontend.
- 76 test Python (auth/billing/admin/gateway; SQLite/FakeNC trong container tạm chỉ đọc source) đạt; 10 mail client tests đạt.
- Mailpit native v1.32.0 build thành công; 38 upstream JS tests đạt, gồm DOMPurify, notification và autocomplete/history. Các file Go nghiệp vụ, go.mod/go.sum/package.json/package-lock.json khớp source gốc; xem apps/mail/UPSTREAM.json. Chỉ metadata phiên bản build có hậu tố CloudBox để cache tài nguyên đúng.
- PHP syntax app theme đạt. Nextcloud integrity:check-core exit 0. 51 app native trước thay đổi được giữ nguyên, thêm đúng cloudbox_theme (manifest so sánh cuối).
- 42 API kiểm tra thật đạt: đăng ký, email xác thực nội bộ, link xác thực HTTPS; đăng nhập/logout/cookie Secure; phân quyền user/admin; 4 route admin; quota/tài khoản chung; Unicode upload/download, favorite, copy/move/rename, trash/restore, version listing, share/public route, chặn anonymous file riêng; SMTP local, search, tags, read/unread, raw/headers/attachment/CID. Tên kiểm tra trong UNIFIED-API-QA.json.
- Browser: portal overview/storage/plans/orders/settings, empty orders, dialog trợ giúp, radio theme bằng phím mũi tên; native app menu, files list/grid, ảnh 300×180 giải mã đúng và PDF.js render trang 1; sidebar chia sẻ/phiên bản, khôi phục bản đầu và đối chiếu byte thật. Native high-contrast (đen #000/trắng #fff), OpenDyslexic, nền cá nhân qua color picker và giữ nền ở trang Files đều được thử bằng tài khoản QA. Màu chủ đạo tiếp tục do native theming xử lý.
- Mail browser: HTML/text/headers/raw/HTML check, attachment/CID, theme radio, Settings native, Deep dark có sẵn được giữ và hiển thị đúng trạng thái Tối trên radio chung. HTML thư vẫn ở iframe sandbox không allow-scripts; không sửa màu/DOM nội dung thư để giả lập dark mode.
- Responsive: 30 phép đo đúng viewport, 3 ứng dụng × light/dark × 1440×1000, 768×1024, 390×844, 320×740, 844×390; không tràn ngang toàn trang tại các màn hình chính đã đo. UNIFIED-responsive.json. Ảnh thực tế trước/sau ở artifacts/design/screenshots/. Đã xem và chỉnh ảnh thực tế, gồm logo NC mobile.
- Mailpit bắt đầu 0 thư. SQLite được snapshot DB/WAL nhất quán và backup qua SQLite API, integrity_check ok, chuyển sang mailpit_data. Hai thư QA sống qua nhiều lần recreate, kể cả chuyển về image native để đối chiếu. Không tạo hộp thư/SMTP độc lập.
- .env, pnpm lock và toàn bộ Python nghiệp vụ portal so với baseline SHA256 không đổi. Không thay tài khoản/tệp/đơn hàng thật, không down -v.

## Lỗi có sẵn và giới hạn — không coi là kiểm tra đạt

1. **Nextcloud 35/viewer 8.0.0**: đóng viewer ảnh có thể ghi `OCA.Files.Sidebar.setFullScreenMode is not a function`; UI vẫn quay về danh sách. Đã tái hiện trên tab mới khi **tắt hoàn toàn cloudbox_theme**, font system, không có CSS theme. Xem UNIFIED-nextcloud-native-baseline-console.json. Không vá bundle/lõi hoặc nâng app để che lỗi.
2. **Version backend native**: sau khi khôi phục bản đầu của tệp QA, byte hiện tại đúng; một timestamp cũ vẫn xuất hiện trong PROPFIND nhưng GET 404, timestamp còn lại GET 200. Kết quả **giống hệt khi bật và tắt theme**, lưu UNIFIED-NATIVE-FINDINGS.json. Không ghi “mọi download phiên bản đều đạt”. Đây là lỗi cần xử lý riêng ở Nextcloud gốc nếu muốn nghiệm thu không còn lỗi native; chưa sửa dữ liệu/version của người dùng để thử.
3. **Console Mail trong trình duyệt tích hợp**: một lỗi MutationObserver/non-Node xuất hiện khi có iframe/chuyển view. Không tìm thấy MutationObserver trong phần mã UI thêm mới. Lần đối chiếu Mailpit gốc chỉ chuyển tab chưa tái hiện; lần chạy bản mới với Settings có ghi lại. Chưa đủ bằng chứng kết luận nguyên nhân thuộc ứng dụng hay công cụ browser. Các tab/nội dung/tải tệp vẫn hoạt động. Xem UNIFIED-browser-console.json và UNIFIED-mail-final-console.json; không tuyên bố console hoàn toàn sạch.
4. Viewer cảnh báo một số MIME chưa bật preview trong cấu hình native. Không bật thêm server preview/Office/relay/spam service chỉ để làm kiểm thử.

Chưa thử Safari/Firefox/trình đọc màn hình, tệp lớn/2 GB, mất mạng giữa upload, external/read-only/federated shares thực, 2FA/SSO, email/relay thật, VNPay tiền thật, toàn bộ app phụ trợ hoặc chaos/SpamAssassin/screenshot export. Guards reduced-motion/forced-colors/blur fallback được kiểm tra trong CSS; chưa có media-emulation ở browser connector để xác nhận toàn bộ các chế độ OS. Không tuyên bố WCAG hoặc kiểm chứng đầy đủ toàn hệ thống.

Thiết kế giữ full renderer/backend native và không làm các lỗi trên thành chức năng giả hoặc link sang cổng cũ. Đã đạt đối chiếu chức năng UI với bản chính trong phạm vi nêu; các lỗi native vẫn được bàn giao rõ, không gọi toàn hệ thống “hoàn tất không lỗi”.

## Vận hành / tái kiểm tra

Từ thư mục dự án chạy start-local.ps1 -NoBrowser. Ba cổng thử phải không có listener của dự án. Khi đang online, script giữ .online/compose.json và hai tunnel đang chạy; đăng nhập portal qua HTTPS. Cổng Mail chỉ bind loopback, không có tunnel. Sau restart xác nhận health, app manifest, mail count và tuyến HTTPS bằng báo cáo UNIFIED-FINAL-VERIFICATION.json.
Source preview/gateway/Dockerfile cũ được giữ làm tư liệu/rollback; không nằm trong Compose hoạt động. Không coi các file đó là cổng còn chạy.

## Chốt sau restart và dọn QA

Đã restart thật portal, nextcloud và mailpit, rồi chạy start-local.ps1 -NoBrowser và scripts/verify-ui.py. Báo cáo cuối UNIFIED-FINAL-VERIFICATION.json xác nhận: năm dịch vụ healthy; 8000/8080/8025 mở, 8001/8081/8026 đóng; tài khoản/thư về đúng số lượng baseline, 51 app native còn nguyên; .env, pnpm lock và backend nghiệp vụ không đổi. Hai tunnel cũ giữ đúng target. Bốn trang public HTTPS và 24 tài nguyên/font tải HTTP 200 sau restart. Một request HTTPS gặp lỗi mạng tạm thời và đạt sau retry có giới hạn, vẫn kiểm chứng TLS; xem transient_http_retries trong JSON.

Hai tài khoản QA, hai thư QA, home/tệp tạm và file credential QA đã được dọn; không tạo đơn hàng QA. Bằng chứng ở UNIFIED-QA-CLEANUP.json. Ảnh sau dọn QA: artifacts/design/screenshots/final-portal-home.png, final-nextcloud-login.png, final-mail-empty.png.

Reduced motion native Nextcloud đã được thử bằng tùy chọn của tài khoản QA: body có reduced-motion, animation của nút 0 giây, transition 0,1 giây. Kiểm tra này không thay thế thử các chế độ OS trên toàn bộ ba UI hoặc nghiệm thu WCAG. Các lỗi native và giới hạn ở trên vẫn còn hiệu lực.