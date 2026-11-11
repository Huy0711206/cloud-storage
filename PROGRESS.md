# Tiến độ CloudBox

## Quyết định hiện hành — 09/11/2026

- Một origin CloudBox; production chỉ `portal` và `db`, lưu trữ native. Nextcloud/Redis legacy và Mailpit development giữ nguồn, không là phụ thuộc vận hành.
- Giữ quota 5/100/500/2048 GiB, giá 0/39.000/89.000/199.000đ và ngân sách thử nghiệm chung 20 GiB. Khởi động Docker/CloudBox thủ công.
- Module Kho tập trung quyền/phạm vi và lifecycle tải lên; xem [thiết kế hiện hành](docs/architecture/STORAGE-MODULE.md). Những quyết định cũ bên dưới là lịch sử và chỉ áp dụng nếu không mâu thuẫn với cập nhật mới.

## Quyết định trước chuyển đổi — lịch sử

- Ba cổng:8000 CloudBox,8080 Nextcloud native,8025 Mailpit native local. Không mở lại preview.
- Giữ dữ liệu/volume/tài khoản/quota/thư; portal và Nextcloud vẫn phiên riêng, không thêm SSO.
- Từ 06/11/2026 dùng Named Tunnel cloudbox-production qua Windows service và docker-compose.named.yml. Giữ .online/.unified-backup private; không tự khôi phục cấu hình Quick Tunnel cũ.
- Viewer có bản vá hai fallback legacy; app signature cảnh báo dự kiến, không tắt integrity. Phiên bản404 là kết luận kiểm thử đã hiệu chỉnh. Mail observer thuộc môi trường iframe/injection chưa xác định module.

## Tái cấu trúc — 01/11/2026

Đã khảo sát trước, trình bày phương án và tạo source snapshot bảo vệ cả thay đổi chưa commit. Đã triển khai cấu trúc apps/packages/infrastructure/scripts/docs/artifacts, giữ root commands và Compose identity. Xem [kế hoạch](docs/architecture/REFACTOR-PLAN.md). Kết quả cuối ở artifacts/qa/refactor-verification.json khi có.

## Lịch sử đầy đủ

[PROGRESS trước tái cấu trúc](docs/history/PROGRESS-before-refactor.md) giữ toàn văn các giai đoạn cũ. Khi mâu thuẫn dùng quyết định hiện hành ở trên và [chẩn đoán mới](docs/qa/DIAGNOSTICS-2026-11-01.md).

## Chốt bàn giao

Đã ánh xạ475tệp, phân nhóm frontend/backend theo feature, giữ vendor/native/legacy coherent và root commands.76Python+10mailclient+17Viewer tests đạt; frontend/nativeMailDocker builds đạt. Production backend hash khớp source đã review;5dịch vụ khỏe, chỉ3cổng chính,17UIassets/fonts local tải200. Giữ các volume/tài khoản và .env/CSV. Người dùng chọn tunnel tắt, đã khôi phục local; không báo HTTPS đã kiểm khi offline. Khắc phục hằng IPV4 bị thiếu trong đợt tách và stale online override bằng kiểm thử. Không xóa source/backup/tài liệu nghi ngờ; xem docs/architecture/FILE-INVENTORY.md. Source rollback snapshot private và full history được giữ. Chi tiết kết quả/giới hạn ở artifacts/qa/refactor-verification.json.

## 06/11/2026 - Fixed domain and pricing UI deployed
- Rebuilt and recreated only portal using docker-compose.yml + docker-compose.named.yml; all five services healthy; public CloudBox HTTP 200 serves main-DaXPdLxo.js.
- Portal BASE_URL=https://cloudbox.rachiba.top; NEXTCLOUD_PUBLIC_URL=https://drive.rachiba.top. start-local prioritizes named override; old private state retained.
- Standard plan uses neutral card border and outline button with primary hover, recommendation badge retained on public/dashboard pricing. Selected-period headline shows total; 12 months billed as 10. TypeScript/Vite build passed.
- No new backups created; no data/volume changes. Visual confirmation of logged-in 1/3/12-month views remains pending.


- Pricing button follow-up: all public plan actions and paid checkout triggers now share plan-outline: neutral background and primary text on hover. Portal rebuilt/deployed; TypeScript/Vite passed; public HTTP 200.

- Corrected pricing hover per user: all plan-outline actions use primary background and white text on hover; neutral default retained. Rebuilt and deployed portal; public new asset main-CbWcvm4G.js verified HTTP 200.

- Nextcloud named-domain migration: added drive.rachiba.top trusted domain and Windows/Docker gateway 172.18.0.1 trusted proxy; overwritehost/CLI URL now drive.rachiba.top, HTTPS conditional on gateway. Login HTTP verified; user login/F5 retest pending.

- Disabled Nextcloud default files for new users: skeletondirectory and templatedirectory explicitly set to empty strings, verified from persisted config. Existing accounts/files untouched; new-account UI retest pending.

## Xác nhận của người dùng và README — 06/11/2026

- Người dùng xác nhận Nextcloud không còn cần F5; liên kết kho tệp, giá kỳ hạn, giao diện gói, tải lên/tải xuống và đăng nhập quản trị thành công.
- Tạm hoãn sửa iPhone 7 Plus/iOS 15; các điện thoại đời mới người dùng đã mượn để thử hoạt động mượt, không suy rộng mọi thiết bị.
- Hoàn thiện README theo Named Tunnel, cách khởi động/build, xử lý 502, bảo vệ dữ liệu và giới hạn kiểm thử. Tự khởi động ổn định vẫn là mục tiêu, chưa cấu hình/xác nhận sau reboot.

- 07/11/2026: after user changed .env database credentials, Portal failed authentication. Verified original credentials retained in existing database container through disposable read-only client; restored only POSTGRES_USER/POSTGRES_PASSWORD in .env, kept VNPay values; Portal recreated healthy, public login HTTP 200. No database passwords or user account passwords changed. VNPay Sandbox configured; payment test pending.

## Kiểm thử nghiệp vụ — 07/11/2026

- Đồng bộ kết nối Nextcloud; 76 backend tests cô lập đạt. 16 tests luồng chạy lại với Nextcloud thật và SQLite tạm đạt, tài khoản QA đã dọn. Callback thanh toán ở các tests này là mô phỏng; không đổi đơn/gói người dùng thật.
- VNPay Sandbox chấp nhận yêu cầu có chữ ký, HTTP 200 trang chọn phương thức Test. Chưa hoàn tất giao dịch thẻ thử qua giao diện public và chưa xác nhận IPN thực tế; công cụ browser timeout. Báo cáo: artifacts/qa/business-qa-2026-11-07.md.

- 07/11/2026: Người dùng hoàn tất thanh toán Sandbox public; đối chiếu đơn 35 paid, basic 1 tháng 39.000đ, có mã giao dịch, quota_synced=true, Nextcloud 100 GB, hết hạn 07/12/2026. Luồng thanh toán public thành công đã đạt; IPN độc lập chưa phân biệt với Return. Giá DB basic/standard hiện 39.000đ/89.000đ khác tài liệu cũ, chờ xác nhận, chưa sửa giá.


## Vận hành tự khởi động — 07/11/2026

- Người dùng xác nhận chủ động đặt basic 39.000đ, standard 89.000đ; giữ nguyên database, cập nhật giá README.
- Tạo scripts/operations/start-on-login.ps1 và tác vụ CloudBox-StartAtLogon sau đăng nhập 30s, Interactive/Limited, không lưu mật khẩu. Chờ Docker, no-build/pull never, check local/Cloudflared/public, log LOCALAPPDATA/CloudBox/logs; retry 3 lần cách 3 phút.
- Chạy CheckOnly đạt; chạy task thực tế LastTaskResult=0, SUCCESS, 2 website HTTP 200 và 5 dịch vụ healthy. Chưa reboot/cold start thực tế. Không đổi chế độ nguồn (AC Never, DC 10 phút). Chưa cấu hình giám sát/cảnh báo liên tục.
- Hướng dẫn: docs/operations/AUTOSTART.md. Không reboot tự động; chờ người dùng lưu công việc và thử đăng nhập lại Windows.


- HOÀN TÁC theo yêu cầu người dùng: đã gỡ tác vụ CloudBox-StartAtLogon và xóa hai tệp vừa thêm scripts/operations/start-on-login.ps1, docs/operations/AUTOSTART.md. Trở lại bật Docker/CloudBox thủ công. Không thay Cloudflared, chế độ nguồn, dữ liệu hoặc giá gói.


## Viền hộp gói — 08/11/2026

- Theo yêu cầu mới: Tiêu chuẩn viền xanh cố định; ba gói khác viền trung tính mặc định và xanh khi hover toàn hộp. Dùng chung plan-border ở LandingPage/PublicPage/PlansPage (1/3/12 tháng). Giữ giá, nhãn, nội dung, nút.
- TypeScript/Vite build đạt; triển khai Portal, giữ phiên bản package Python khớp container trước triển khai (đã đối chiếu). Browser public xác minh từng hover Miễn phí/Cơ bản/Cao cấp xanh, rời chuột về trung tính, Tiêu chuẩn luôn xanh. Trang dashboard áp dụng cùng class/CSS, chưa thử trực tiếp phiên đăng nhập trong lượt này.



## 09/11/2026 — CloudBox lưu trữ độc lập (quyết định hiện hành)

- Theo prompt người dùng đã duyệt: loại bỏ phụ thuộc Nextcloud, chỉ CloudBox cho giao diện/tệp/xác minh. Quyết định này thay mô hình ba dịch vụ công khai cũ.
- Đã xây OTP Gmail, khôi phục mật khẩu, lưu trữ blob/metadata độc lập, quota theo gói, upload khối, chia sẻ chỉ đọc, thùng rác/khôi phục/xóa vĩnh viễn và đọc phiên bản đã chuyển.
- 55 kiểm thử cô lập và 3 kiểm thử PostgreSQL đồng thời đạt; frontend check/build đạt. Gmail thật đã gửi trong luồng thử riêng và người dùng xác nhận nhận thư.
- Chuyển thử và chuyển chính kiểm checksum 328 tệp + 8 phiên bản, 15 thư mục, 2 mục thùng rác, giữ 542 dòng metadata lịch sử. Ánh xạ 64 tệp quản trị nguồn vào quản trị CloudBox theo chỉ định. Giữ nguyên 14 tài khoản, 6 đơn, 2 paid và giá hiện hành.
- Hai dịch vụ production db/portal healthy. Nextcloud/Mailpit/Redis dừng, source volumes và DB cũ giữ nguyên. Không thêm tự khởi động, không thuê cloud, không sửa secret hoặc tạo backup mới.
- Public trang chủ/đăng nhập đã xem được trong browser. Chờ kiểm tra UI tài khoản cũ và gỡ route/DNS miền drive trên Cloudflare; không tuyên bố đã hoàn tất hai bước này. Xem artifacts/qa/native-cloudbox-2026-11-09.md.

- Sửa lỗi đăng nhập thật trong IAB: Origin null được kiểm bằng CSRF token gắn phiên + Fetch Metadata same-origin, không mở chung nguồn null. 67 tests + 3 PostgreSQL riêng đạt; browser thử dữ liệu chẩn đoán đã qua guard, chờ đăng nhập tài khoản cũ.

- Người dùng đăng nhập tài khoản cũ thành công sau bản sửa CSRF; browser xác nhận gói 100 GB và đơn cũ, kho nội bộ, danh sách và phiên bản tệp, giá kỳ 1/3/12 tháng đúng. Cloudflare đang chờ người dùng đăng nhập để gỡ hostname/DNS cũ.

- Hoàn tất bước Cloudflare ngày 09/11/2026: sau xác nhận tại bước xóa, đã gỡ route drive.rachiba.top (8080) và Cloudflare tự xóa CNAME đi kèm. Tunnel chỉ còn CloudBox (8000); đã tải lại kho trong phiên người dùng, gói 100 GB vẫn đúng. Không đổi token hoặc dịch vụ khác. Các dòng chờ Cloudflare ở trên là lịch sử đã được xử lý.


## 09/11/2026 — Quyền lợi gói và ngân sách thử nghiệm

- Người dùng duyệt hạn mức 1/3/5/10 GB, áp dụng ngay tài khoản cũ; giá giữ nguyên; tổng ngân sách 20 GiB.
- Bổ sung bảng quyền lợi dùng chung, hết hạn kiểm tại API, phiên bản tự động/khôi phục bảo vệ bản hiện tại, mật khẩu/hạn dùng liên kết, nhận tệp chỉ gửi, nhóm và thống kê tổng hợp. Schema mới chỉ thêm bảng, không ALTER/copy lại kho.
- Kiểm thử trong dữ liệu riêng: 101 tests SQLite/filesystem đạt, 5 PostgreSQL concurrency riêng đạt; frontend check/build đạt. Đã kiểm tra IAB với tài khoản giả: giá 1/3/12 tháng, bảng quyền lợi, 390px, nhóm/biểu mẫu nhận tệp.
- Đã sửa lỗi khởi động Docker socket, giữ nguyên DB/volumes. Không tạo backup mới hoặc bật tự khởi động. Chi tiết triển khai/đối chiếu nằm trong artifacts/qa/plan-benefits-2026-11-09.md.


## 09/11/2026 — Khôi phục hạn mức theo yêu cầu mới nhất

- Khôi phục 5/100/500/2048 GiB (5 GB/100 GB/500 GB/2 TB) cho cả tài khoản hiện có, thay quyết định giảm hạn mức trước đó. Giữ nguyên giá, quyền lợi và tổng ngân sách thử nghiệm 20 GiB; không cấp thêm dung lượng ổ đĩa thật.
- Giao dịch cập nhật chỉ sửa plans.quota_gb, đối chiếu giữ nguyên tài khoản, đơn, metadata tệp/phiên bản.
- Đã triển khai: Portal healthy, HTTPS 200; bootstrap công khai và runtime đều đúng 5/100/500/2048 GiB, pool 20 GiB. 18 kiểm thử quota/thanh toán riêng đạt; đối chiếu giữ nguyên 14 tài khoản, 6 đơn, 343 mục và 8 phiên bản.

## 09/11/2026 — Tinh gọn module Kho: quyền và giao dịch tải lên

- Tập trung actor/chủ dung lượng/phạm vi/thành viên/gói vào `storage/access.py`; lifecycle cá nhân/nhóm/nhận tệp vào `storage/uploads.py`. Giữ interface native_service và URL; caller không tự thay actor bằng sponsor. Bỏ vòng đời lặp, preflight lặp và commit gắn nhóm riêng sau khi tạo phiên.
- Session, liên kết nhóm/yêu cầu và replacement cùng giao dịch metadata. Kiểm lại quyền ở từng giai đoạn; namespace nhóm bị từ chối qua API cá nhân kể cả phiên nhóm cũ chưa gắn scope. Khóa User theo ID trước khóa ngân sách; bảo trì tài khoản đã khóa vẫn dọn được phiên hết hạn.
- Bảo vệ retry sau rename/commit lỗi và sau mất xác nhận commit, không xóa blob đang được tham chiếu. Khôi phục giữ bản hiện tại và lịch sử; không sửa chính sách tự xóa lịch sử nhập cũ.
- 175 kiểm thử SQLite/filesystem + 8 PostgreSQL `cloudbox_qa` riêng đạt; candidate startup/assets/API đạt. Không đổi frontend/dependency/schema hoặc giao dịch thanh toán. Giữ cảnh báo deprecation cũ.
- Đã recreate riêng Portal trong Compose identity cũ; db/portal healthy, local/public health/home/login/assets 200, API tệp chưa đăng nhập 401. Fingerprint giữ nguyên toàn bộ 14 tài khoản/6 đơn/4 gói/343 node/8 version/545 migration rows và metadata storage; 336 blob khớp checksum trước/sau. Schema/.env/Compose/DB container/mount/network/UI assets giữ nguyên.
- Cập nhật README, GLOSSARY, ADR và danh mục caller/đợt sau. Chưa gộp frontend hoặc xóa legacy. Không tạo backup mới, không sửa secret/Cloudflare/autostart/volume/dữ liệu nguồn. Xem [báo cáo](artifacts/qa/storage-refactor-2026-11-09.md) và [thiết kế module](docs/architecture/STORAGE-MODULE.md).

## 09/11/2026 — Dọn cây source và build

- apps chỉ còn Portal; 286 tệp/3.510.906 bytes chuyển sang legacy hoặc khu vực one-off, không phải source bị xóa. 243 tệp là upstream Mailpit. Xóa riêng 10 generated assets cũ/696.438 bytes; 0 source file bị xóa.
- Tách optional Compose, main/legacy TypeScript/build; giữ tên nghiệp vụ đã rõ. Chặn Quick Tunnel/rollback/verifier lịch sử; generator chỉ sinh CloudBox. Giữ root compatibility entry với thông báo thay thế.
- Kiểm lại175 backend +8 PostgreSQL +45gateway +10mail API tests đạt; main/optional frontend builds, clean Docker build và candidate startup đạt. UI compiled assets khớp byte; không deploy/restart hoặc thay dependency vận hành.
- Fingerprint DB/blob/schema/.env/default Compose/container/image/mount/network/runtime source/UI giữ nguyên. Không backup hoặc sửa dữ liệu thật. Chi tiết: artifacts/qa/structure-cleanup-2026-11-09.md.

## 10/11/2026 — Xóa source không còn cần thiết

- Người dùng xác nhận bỏ nhóm chức năng tham khảo cũ. Xóa thực327 source/reference files (243vendor),3.752.771bytes;8cache .pyc/95.710bytes; không di chuyển source hoặc tạo backup mới.
- Bỏ5 dependency trực tiếp,4 package scripts và6 compatibility CLI cũ. Frontend bỏ41 khai báo hàm, giữ13 symbol nội bộ; backend bỏ133 unused imports và5 helper cũ. Giữ importer/models/schema và bảo vệ native không gọi mạng ngoài.
- Knip5.70/Vulture2.14 chạy riêng trong QA.176backend +8PostgreSQL tests đạt; tsc noUnusedLocals/Vite và clean Docker build đạt. Public desktop1440/mobile390 không khác biệt trong tập DOM/layout/style đo.
- Đã cập nhật riêng Portal với dependency production giữ nguyên; HTTPS200, DB/volume/.env/Compose/fingerprint metadata và336blob giữ nguyên. Vulture còn59 advisory framework/model; không tuyên bố sạch tuyệt đối. Báo cáo: artifacts/qa/deadcode-cleanup-2026-11-10.md.

## 10/11/2026 — Chốt cấu trúc và hướng dẫn hiện hành

- Xóa3 thư mục rỗng và1 cache online cũ/12.294bytes. Sửa docs development/operations/README/STORAGE-MODULE; gắn nhãn6 tài liệu lịch sử; dọn ignore output cũ và sửa thông báo -RebuildMail. Không đổi nghiệp vụ/UI.
- Sửa node_modules metadata còn trỏ checkout portal/frontend cũ bằng pnpm frozen install; không đổi hash package/lock/requirements hoặc phiên bản. pnpm check/build hoạt động;16asset khớp byte với runtime.
- Kiểm25 link hiện hành, wrapper/parser/entry/testpaths/manifest và Knip graph đạt. Fingerprint DB/blob/.env/Compose/container/image/mount/network/runtime giữ nguyên. Không deploy/restart và không chạy lại test backend/PG không liên quan.
- Build tái lập, hoàn thiện test luồng và gom lệnh pre-deploy là ba đề xuất tiếp theo, chưa thực hiện. Báo cáo: artifacts/qa/structure-final-2026-11-10.md.


## 10/11/2026 — Chuyển production sang AWS Academy

- Theo xác nhận người dùng: tạo riêng EC2 cloudbox-app-01, Ubuntu 24.04/t3.small/40 GiB EBS mã hóa, CPU Standard; giữ nguyên năm EC2 cũ. Cài Docker/Compose từ nguồn chính thức và dùng nguyên image Portal/PostgreSQL.
- Người dùng tự nhập secrets trực tiếp trên EC2. Cấp tunnel cloudbox-aws-ec2 riêng và chuyển CNAME cloudbox.rachiba.top sau kiểm chứng; không đổi miền công khai hoặc mở cổng DB/web trên Internet.
- Dừng Portal laptop để chốt dữ liệu. Toàn bộ 21 bảng/schema/sequence và 336 blob khớp trước/sau startup; giữ 14 tài khoản/6 đơn/4 gói/343 node/8 version/545 migration rows, giá/quota/pool. .env, DB và volumes nguồn giữ nguyên, không thay tự khởi động Windows.
- EC2 db/portal healthy, tunnel ready; public browser home/health/auth guard đạt. Gmail TLS/authentication đạt, không gửi thư thử hoặc tạo giao dịch mới. Python urllib bị Cloudflare 1010, không làm yếu bảo vệ để ép pass.
- Người dùng xác nhận đăng nhập tài khoản cũ, mở kho, tải lên/tải xuống thành công. AWS Academy vẫn có giới hạn phiên/ngân sách; chưa cam kết 24/7 hoặc có backup dài hạn. Không rollback trực tiếp về bản dữ liệu laptop đã cũ.
- Hướng dẫn: docs/operations/AWS-ACADEMY.md; báo cáo: artifacts/qa/aws-deployment-2026-11-10.md. Ba đề xuất dependency lock/test bổ sung/pre-deploy từ lượt trước chưa triển khai.

- Sau xác nhận người dùng kiểm thử đạt: đã kiểm hash và xóa archive/dump vận chuyển tạm trên hai máy và trong /tmp container DB, xóa bản token tunnel tạm laptop; giữ runtime secrets EC2, khóa SSH cần thiết và toàn bộ dữ liệu nguồn.


## 10/11/2026 — Viết lại hướng dẫn Docker và triển khai cho dễ đọc

- Đưa Start Lab → EC2 Running → mở web lên đầu README; phân biệt Docker Engine EC2 với Docker Desktop laptop và ba dịch vụ portal/db/tunnel.
- Tách mở web, sửa lỗi khởi động, cập nhật image và chuyển sang máy mới; từng khối lệnh ghi rõ PowerShell laptop/Bash EC2. Chỉnh hướng dẫn Gmail về portal.env trên EC2 thay vì .env laptop; bỏ chỉ dẫn lỗi 502 phải mở Docker laptop ở mục hiện hành.
- Giữ chi tiết nghiệp vụ/migration/lỗi Windows lịch sử trong các mục mở rộng; nêu đúng ngoại lệ restart unless-stopped và giới hạn phiên Academy.
- Chỉ sửa tài liệu, không Start Lab, không SSH hoặc chạy các lệnh triển khai/build, không thay config/dữ liệu/source nghiệp vụ. Kiểm link và đối chiếu lệnh với Compose/Dockerfile; không chạy lại test ứng dụng không liên quan.
