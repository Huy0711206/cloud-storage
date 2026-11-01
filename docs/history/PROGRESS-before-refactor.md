# CloudBox — tiến độ và bàn giao cho chat tiếp theo

Cập nhật: **31/10/2026 — Asia/Bangkok**.

Tài liệu này tổng hợp công việc đã hoàn thành và các kết quả kiểm tra của phiên triển khai trước. Việc tạo file này không bao gồm chạy lại Docker hoặc kiểm thử lại ứng dụng hôm nay. Chat tiếp theo cần kiểm tra trạng thái thực tế trước khi kết luận dịch vụ đang chạy.

## 1. Đọc nhanh

- Dự án: bài tập lớn **Cloud Data Storage**, tên ứng dụng **CloudBox**.
- Frontend CloudBox mới đã có ở **8001**; hộp thư mới đã có ở **8026**.
- Giữ bản CloudBox chính **8000**, Mailpit gốc **8025**, Nextcloud **8080**.
- **Mới: CloudBox Files ở 8081**, dùng chung Nextcloud 8080; đọc mục 12 và FILES-QA.md.
- **8002 đã ngừng sử dụng.** Không cần thêm server dev để chạy bản Docker.
- Các cổng thử giao diện dùng dữ liệu chung, không phải môi trường dữ liệu độc lập hoặc máy chủ dự phòng.
- **Mẫu email xác thực chưa thiết kế lại**; người dùng yêu cầu để làm sau.
- Domain, PC/VPS và phương án online chưa chốt. Không tự bật tunnel.
- Việc tiếp theo: kiểm tra hệ thống nếu đã tắt, nhận phản hồi UI; chỉ sửa mẫu email hoặc chuyển bản thử sang bản chính khi người dùng yêu cầu.

## 2. Vị trí và nguyên tắc làm việc

Dự án thật trên laptop, cũng là thư mục mở bằng VS Code:

```text
C:\Users\jnguyen\Downloads\ĐH Mở\DTDM\Bai Tap Lon\cloud-storage
```

Workspace của chat khác với dự án thật:

```text
C:\Users\jnguyen\.codex\.chatgpt-projects\g-p-6ae1bd0d9be4819199a663315a01a6cb
```

- Chỉnh trực tiếp dự án thật; không tạo bản sao toàn bộ dự án ở nơi khác.
- Tuân thủ AGENTS.md hiện hành. Các file đồng bộ trong `sources/` của workspace chỉ để tham khảo, không sửa, di chuyển hoặc xóa.
- Ghi vào dự án thật có thể cần quyền công cụ vì nằm ngoài workspace được cấp quyền ghi.
- Không in mật khẩu, token hoặc toàn bộ `.env`. Giữ dữ liệu và Docker volumes.
- Trao đổi với người dùng bằng tiếng Việt, giải thích dễ hiểu và báo rõ kết quả đã kiểm chứng.

## 3. Mục tiêu và kiến trúc hiện có

Bài tập yêu cầu hệ thống lưu trữ đám mây có frontend/backend, đăng ký, billing và thanh toán. Đề gợi ý ownCloud, Nextcloud, Seafile và Garage; yêu cầu triển khai online cụ thể vẫn cần xác nhận với giảng viên.

Ứng dụng hiện sử dụng:

- React, TypeScript, Tailwind CSS, shadcn/ui cho frontend.
- FastAPI cho tài khoản, gói dịch vụ, đơn hàng và tích hợp dịch vụ.
- PostgreSQL lưu metadata/nghiệp vụ của portal và database Nextcloud.
- Nextcloud quản lý tệp, người dùng kho và hạn mức; Redis hỗ trợ Nextcloud.
- Mailpit nhận email thử nghiệm qua SMTP.
- VNPay có luồng checkout/return/IPN và kiểm tra chữ ký; chưa kiểm thử giao dịch tiền thật.

Cloudflare Tunnel và object storage là hai vai trò khác nhau. Chưa chuyển hệ thống sang R2/Garage hoặc máy chủ cloud; không coi các phương án đã thảo luận là đã triển khai.

## 4. Cổng và dịch vụ đã chốt

| Cổng | Dịch vụ | Vai trò |
|---|---|---|
| 8000 | `portal` | CloudBox chính, giao diện ổn định |
| 8001 | `portal-preview` | Frontend CloudBox thử nghiệm, nghiệp vụ chuyển về portal |
| 8002 | Không dùng | Môi trường QA cũ đã dừng |
| 8080 | `nextcloud` | Giao diện quản lý tệp |
| 8025 | `mailpit` | Giao diện hộp thư gốc |
| 8026 | `mail-preview` | CloudBox Mail mới, chuyển API tới Mailpit |
| 5432 | `db` | PostgreSQL nội bộ Docker, không công bố ra laptop |

8001 từng được gọi là cổng backup, nhưng yêu cầu mới đã chuyển thành **bản thử giao diện**.

- 8000/8001 dùng chung backend, tài khoản, database và Nextcloud. Các thao tác nghiệp vụ ở 8001 tác động dữ liệu chung.
- 8025/8026 dùng chung hộp thư. API mở chi tiết thư sẽ đánh dấu đã đọc; xóa hoặc đổi trạng thái ảnh hưởng cả hai giao diện.
- Các service mới bind `127.0.0.1`; không tự công khai Internet.
- `BASE_URL` của backend là địa chỉ chuẩn tạo email xác thực và callback thanh toán, hiện cấu hình cục bộ theo 8000.

## 5. Công việc đã hoàn thành

### 5.1. Khắc phục khởi động

- Xử lý mật khẩu PostgreSQL không khớp `.env`. Đổi `.env` đơn thuần không tự đổi mật khẩu role đã tồn tại.
- Người dùng đã cho phép đồng bộ mật khẩu quản trị Nextcloud theo `.env`, để portal gọi API đúng.
- Sửa Nextcloud chuyển hướng từ 8080 sang cổng 80: cấu hình địa chỉ cục bộ dùng `localhost:8080`, protocol HTTP và CLI URL tương ứng.
- Thêm script chạy hệ thống, đợi Docker và health checks, không cần mở nhiều terminal.
- Sửa kiểm tra URI Nextcloud để hỗ trợ khác biệt giữa Windows PowerShell và PowerShell mới.

### 5.2. CloudBox tại 8001

- Giao diện Modern SaaS Dashboard: trang công khai, đăng nhập/đăng ký, dung lượng, gói, đơn hàng, tài khoản và quản trị.
- Light/dark mode, responsive, menu mobile, trạng thái tải/rỗng/lỗi, dialog và focus bàn phím.
- Liquid Glass nhẹ ở cụm công cụ; nội dung/form dùng nền dễ đọc.
- Build variant `VITE_UI_VARIANT=preview`; build mặc định giữ App ổn định.
- Gateway 8001 thay asset frontend và chuyển tiếp nghiệp vụ tới portal, không tạo backend nghiệp vụ hoặc maintenance job thứ hai.
- Đợt này giữ nguyên image/asset đang chạy ở 8000.

### 5.3. CloudBox Mail tại 8026

- Xác minh Mailpit đang chạy **v1.32.0**, tham khảo Swagger thực tế và tài liệu chính thức.
- Desktop ba vùng; tablet thu gọn điều hướng; mobile tách danh sách và nội dung, có nút quay lại.
- Danh sách, tìm kiếm, lọc chưa đọc/tệp đính kèm và phân trang 20 thư.
- Đọc HTML/text, xem headers/nguồn, tải tệp đính kèm và EML.
- Đánh dấu đã đọc/chưa đọc; xóa thư có xác nhận, khóa thao tác trong lúc xử lý.
- Poll REST mỗi 10 giây khi tab hiển thị; không tự mở chi tiết thư khi poll.
- Theme lưu riêng theo origin; loading/empty/error, mất kết nối và thư không tồn tại.
- HTML qua allowlist, iframe `sandbox=""` và CSP. Không thực thi script, form, liên kết hoạt động hoặc tải tài nguyên ngoài.
- CID dạng raster có thể nằm trong cả `Inline` và `Attachments`; tải có giới hạn rồi chuyển thành **data URL**. Không thêm `allow-same-origin`.
- Gateway chỉ mở các API cần thiết, yêu cầu ID cụ thể cho mutation; không mở send/relay/release hoặc xóa toàn bộ khi thiếu ID.

Các lỗi đã sửa trong quá trình làm hộp thư:

1. PUT/DELETE Mailpit trả `text/plain: ok`, cần nhận đúng thay vì luôn parse JSON.
2. Poll nền không được hủy request đang chạy trước timeout, gây chờ mãi khi phản hồi chậm.
3. Cập nhật trạng thái cần kiểm tra ID thư; dialog xóa giữ ID đích khi mở.
4. Ảnh CID có thể là attachment; blob URL không hiển thị trong iframe opaque của lần kiểm tra nên đã đổi sang data URL.
5. PNG trong fixture QA từng có CRC sai, đã sửa và xác minh ảnh hiển thị.

## 6. Bản đồ mã nguồn

Các đường dẫn dưới đây tương đối với **thư mục dự án thật** ở mục 2:

| File/thư mục | Nội dung |
|---|---|
| `README.md` | Cách chạy/build/dừng, ý nghĩa các cổng và xử lý lỗi |
| `docker-compose.yml` | Các service, mạng, volumes và ánh xạ cổng |
| `start-local.cmd`, `start-local.ps1` | Khởi động Docker và kiểm tra dịch vụ |
| `portal/app/` | Backend CloudBox; không chứa backend Mailpit |
| `portal/app/emailer.py` | Email xác thực/biên nhận hiện tại; xác thực vẫn là văn bản thuần |
| `portal/frontend/src/App.tsx` | App ổn định và các điểm ghép giao diện |
| `portal/frontend/src/preview/` | Giao diện CloudBox thử nghiệm 8001 |
| `portal/preview.py`, `portal/Dockerfile.preview` | Gateway và image 8001 |
| `portal/frontend/src/mail/` | UI 8026: MailApp, MessageReader, API, types, CSS và cô lập HTML |
| `portal/mail_gateway.py` | Gateway API Mailpit và phục vụ frontend 8026 |
| `portal/Dockerfile.mail-preview` | Image riêng cho hộp thư mới |
| `portal/frontend/vite.mail.config.ts` | Build riêng vào `dist-mail` |
| `portal/tests/` | Test backend/gateway và fixture QA |
| `portal/frontend/tests/mail-api.test.mjs` | 10 test API client, không gọi Mailpit thật |
| `portal/frontend/PREVIEW-DESIGN.md`, `PREVIEW-QA.md` | Thiết kế và QA của 8001 |
| `portal/frontend/MAIL-DESIGN.md`, `MAIL-QA.md` | Thiết kế và QA của 8026 |

Giữ package manager pnpm, phiên bản theo lockfile và component hiện có; không tự nâng cấp thư viện chỉ để chỉnh UI. Có các skill design, frontend-design, liquid-glass-react, shadcn, tailwind-css, ui-styling, ui-ux-pro-max và REA; dùng theo phạm vi phù hợp của yêu cầu mới.

## 7. Cách chạy lại

Tại thư mục dự án thật:

```powershell
# Chạy hằng ngày
.\start-local.cmd

# Chỉ khi cần build lại phần tương ứng
.\start-local.cmd -Rebuild         # portal 8000
.\start-local.cmd -RebuildPreview  # UI thử 8001
.\start-local.cmd -RebuildMail     # hộp thư 8026

# Xem trạng thái
docker compose ps
```

Giữ Docker Desktop chạy khi dùng ứng dụng. Sau khi lệnh thành công có thể đóng terminal. Không chạy các cờ build nếu chỉ cần mở lại hệ thống.

Frontend có thể chạy `pnpm check` và `pnpm run test:mail`; test client dùng Node 24+. Trên laptop từng sử dụng Node/pnpm do môi trường Codex cung cấp, nên cần kiểm tra PATH nếu lệnh không có sẵn. Để sử dụng ứng dụng bằng Docker, không cần cài thêm Node/Python cho Windows.

## 8. Bằng chứng kiểm tra cuối phiên triển khai

- **55 test Python + 10 test client API đạt**. Còn một cảnh báo deprecation httpx/Starlette, không làm test thất bại.
- TypeScript và build image riêng đạt; khung đọc thư được tách tải thành chunk riêng.
- Chromium: 1440×1000, 768×1024, 390×844, 320×780 và 844×390 không tràn ngang.
- HTML/text/headers/nguồn, đọc/chưa đọc, tìm kiếm/reset và phân trang 25 thư hoạt động.
- Xóa thư QA thành công; mở lại ID đã xóa có thông báo và đường quay lại.
- Thư mới tự xuất hiện, lỗi mất kết nối có thông báo và phục hồi sau khi backend QA trở lại.
- Ảnh CID có `naturalWidth=1` với PNG mẫu; iframe không có script/form/link hoạt động/ảnh HTTP.
- Endpoint tải TXT trả 187 byte, đúng Content-Disposition; EML trả nội dung và tên `.eml` đúng. Không coi đây là xác minh đầy đủ nơi trình duyệt lưu file tải xuống.
- Nút mobile được kiểm tra 44px; Escape đóng dialog và trả focus; skip link tới main; theme giữ sau reload.
- Script khởi động kiểm tra đạt 8000, 8001, 8025, 8026 và 8080.
- Hai container Mailpit/UI QA đã xóa, 8026 đã nối Mailpit thật. **Hộp thư thật giữ nguyên 0 thư / 0 chưa đọc.** Không gửi thư QA ra Internet.
- Asset đang chạy ở 8000/8001 giữ nguyên; 8002 không có listener tại lần kiểm tra đó.

Ảnh QA được lưu ở workspace của chat, tên `cloudbox-mail-desktop.jpg` và `cloudbox-mail-mobile-dark.jpg`. Đây là ảnh dữ liệu mẫu, không phải thư thật.

## 9. Việc còn mở và giới hạn

- Không có lỗi chặn đã biết ở cuối phiên; chưa kiểm tra lại runtime khi tạo tài liệu này.
- Safari, Firefox và trình đọc màn hình chưa được kiểm tra trực tiếp.
- Reduced motion đã rà soát CSS/media query, chưa giả lập tùy chọn hệ điều hành; không tuyên bố đạt WCAG đầy đủ.
- Chưa kiểm thử VNPay bằng tiền thật hoặc xác nhận cấu hình merchant sẵn sàng sử dụng thực tế.
- Domain, triển khai PC/VPS và yêu cầu online của giảng viên chưa chốt.
- Chưa thiết kế HTML cho email xác thực; không nhầm việc này với UI hộp thư 8026 đã hoàn thành.

## 10. Bước tiếp theo cho chat mới

1. Đọc file này và README, kiểm tra trạng thái Docker/dịch vụ nếu cần.
2. Nhận phản hồi của người dùng về 8001/8026 và sửa đúng phần được yêu cầu.
3. Không tự thay bản chính 8000/8025 bằng bản thử, không tự bật tunnel hoặc đổi SMTP.
4. Nếu người dùng tiếp tục phần email xác thực: khảo sát `portal/app/emailer.py`, đề xuất mẫu trước, giữ bản text fallback và không thao tác tài khoản thật để thử.
5. Kiểm tra thêm các giới hạn trình duyệt/a11y, rồi chốt phương án triển khai online khi yêu cầu rõ.

Khi có thay đổi mới, cập nhật ngày, trạng thái và bằng chứng tại đây; phân biệt kết quả đã chạy kiểm tra với việc còn dự kiến.

## 11. Kiểm tra tiếp nhận trong chat mới — 31/10/2026

Đã đọc bản bàn giao, PROGRESS.md, README.md, docker-compose.yml và start-local.ps1 tại dự án thật.

Kết quả kiểm tra thực tế trong chat mới:

- Docker Compose: cả 7 dịch vụ db, redis, nextcloud, mailpit, portal, portal-preview và mail-preview đang chạy, đều healthy.
- GET /healthz tại 8000, 8001, 8026 trả HTTP 200 và status=ok; variant lần lượt là mặc định, preview, mail-preview.
- Trang chủ tại 8000, 8001, 8026 đều trả HTTP 200.
- Mailpit 8025: API danh sách trả HTTP 200, total=0, unread=0. Không mở chi tiết, gửi, sửa hoặc xóa thư.
- Nextcloud 8080: trang chủ chuyển tới http://localhost:8080/login, HTTP 200, đúng cổng.
- Không cần khởi động hoặc build lại. Không thay mã ứng dụng, cấu hình, tài khoản hoặc dữ liệu; không bật tunnel.
- Chưa chạy lại bộ test Python/frontend và chưa kiểm tra UI trực quan hoặc trình duyệt bổ sung trong lần tiếp nhận này; kết quả test mục 8 vẫn là bằng chứng của phiên trước.

Bước tiếp theo vẫn là nhận góp ý giao diện 8001/8026. Chưa có yêu cầu mới để chuyển bản thử sang bản chính, thiết kế email xác thực hoặc triển khai online.


## 12. CloudBox Files 8081 — triển khai ngày 31/10/2026

Yêu cầu mới đã được thực hiện: frontend quản lý tệp React/TypeScript/Tailwind/shadcn riêng tại **127.0.0.1:8081**, kết nối Nextcloud 35.0.2 hiện có qua FastAPI gateway files-preview. Giữ 8080 gốc, không sửa lõi/mount đè volume Nextcloud; không rebuild các image portal/portal-preview/mail-preview.

- Đã đọc và áp dụng design, frontend-design, ui-ux-pro-max, shadcn, Tailwind, ui-styling và liquid-glass-react theo phạm vi. Khảo sát API bằng tài liệu chính thức và mã Nextcloud cần thiết; không cần cài REA.
- Thiết kế đã trình bày trước khi code; UI lấy danh sách tệp làm trọng tâm, đồng bộ CloudBox, responsive/light-dark; kính nhẹ ở cụm kiểu xem, fallback mobile/reduced-motion.
- Đăng nhập chính thức Login Flow v2 tại 8080; UID qua OCS, app password giữ RAM server, opaque HttpOnly cookie Path=/api/files, Origin gồm cổng + CSRF. Một worker, phiên 8 giờ. Có dọn phiên và thử thu hồi token do luồng tạo. Không chứa credential quản trị trong service mới.
- Duyệt, upload/download, tạo/đổi tên/sao chép/di chuyển, yêu thích, chọn nhiều, xóa/khôi phục, hạn mức và trạng thái quyền. Chống ghi đè tên. Khôi phục dùng xử lý đích ảo Nextcloud 35 đã xác minh, không áp dụng Overwrite:T cho MOVE/COPY thông thường.
- Tìm kiếm trong danh sách; ảnh raster/văn bản có xem trước. Chia sẻ nâng cao/PDF/Office/video/lịch sử và tiện ích chưa có UI riêng dùng Nextcloud gốc. Không nút giả, không xóa vĩnh viễn trong gateway.
- Đã thêm -RebuildFiles vào start-local, build:files vào frontend, service Compose, exclude dist-files khỏi build context/Git. Lockfile và phiên bản thư viện giữ nguyên.
- **76 test Python + 10 test frontend client đạt**; TypeScript/build Docker đạt. Test Python dùng SQLite/FakeNC trong container tạm chỉ đọc source, không database thật.
- Thử API thật bằng tài khoản Nextcloud QA dùng một lần: đăng nhập/v2 cấp quyền/poll/logout, quota, Unicode upload/download, chống ghi đè, favorite, copy/move/rename, trash/restore và share read. Browser: upload tên dài, tạo bằng bàn phím, tìm kiếm, list/grid, image/text preview, xóa/khôi phục, mobile menu, light/dark, lỗi 404; không tràn ngang ở 1440/768/390/320/landscape.
- Ảnh QA ở workspace chat: cloudbox-files-desktop.png, cloudbox-files-mobile-dark.png. Đây là dữ liệu tài khoản QA.

Tài liệu mới: portal/frontend/FILES-DESIGN.md, FILES-QA.md; mã portal/files_gateway.py, frontend/src/files/, Dockerfile.files-preview, vite.files.config.ts, tests/test_files_gateway.py. README mục 12 ghi cách dùng/build/dừng và giới hạn phiên.

Chưa thử Safari/Firefox/screen reader, reduced-motion qua OS, tệp sát 2 GB, gián đoạn giữa upload lớn, 2FA/SSO thật hoặc external/read-only shares. Không tuyên bố WCAG đầy đủ. Mất RAM/restart cần đăng nhập lại; khi kill/mất mạng lúc thu hồi, quyền có thể cần xóa tại Nextcloud → Bảo mật.

Bước tiếp theo: người dùng xem và góp ý **8081**, cùng 8001/8026 nếu cần. Chưa chuyển bản thử sang 8080, chưa bật tunnel, chưa thiết kế mẫu email xác thực hoặc triển khai online.

### Xác minh bàn giao cuối mục 12

- start-local.ps1 -NoBrowser chạy thành công, không build: health 8000/8001/8026/8081 và Mailpit 8025 đều đạt; Nextcloud 8080 trả HTTP 200 tại http://localhost:8080/login.
- Docker Compose có 8 service đang chạy và healthy, chỉ files-preview là service mới. Các container chính trước đó không bị recreate trong lần kiểm tra cuối.
- Login Flow v2 được chạy lại thành công trên image cuối, bao gồm list và logout.
- Đã đăng xuất phiên trình duyệt QA, xóa đúng tài khoản cloudbox-files-qa-* vừa tạo và xác minh tài khoản không còn tồn tại; toàn bộ tệp của tài khoản QA được dọn. Đã xóa tệp credential QA cục bộ.
- Mailpit thật vẫn total=0, unread=0; không gửi email QA.
- git diff --check đạt. README/PROGRESS có sẵn từ trước được giữ nội dung và bổ sung, không commit tự động.
- Trang 8081 để ở màn hình đăng nhập để người dùng dùng tài khoản hiện có. Đã lưu ảnh desktop/mobile của dữ liệu QA trước khi dọn.


## 13. Truy cập Internet bằng Quick Tunnel — 31/10/2026

Người dùng đã cho phép bật tunnel trong lần này, thay cho quyết định giữ tunnel tắt trước đây. Chỉ công khai CloudBox chính 8000 và Nextcloud gốc 8080. Các bản thử 8001/8081, hộp thư 8025/8026, database và Redis không có public tunnel.

Kết quả khảo sát: có script start-online.ps1 cũ dùng Quick Tunnel và image cloudflare/cloudflared đã cài (version 2026.10.5). Trước lần bật này không có tunnel container hoặc tiến trình cloudflared đang chạy; chưa tìm thấy domain cố định được cấu hình trong dự án, các biến địa chỉ công khai trong .env đang là localhost, thư mục profile .cloudflared không cung cấp cấu hình domain/tunnel có tên. Đây không phải kết luận người dùng chưa đăng ký domain ở nơi khác. Không thấy URL Quick Tunnel cũ cụ thể còn dùng được.

Địa chỉ đã xác minh trong phiên này (có thể đổi khi khởi tạo lại):
- CloudBox: https://enjoying-amsterdam-envelope-convergence.trycloudflare.com
- Nextcloud: https://seemed-reggae-ultimate-johnston.trycloudflare.com

### Chạy và dừng

Tại thư mục dự án, Docker Desktop đang chạy:

```powershell
# Bật ứng dụng nếu đang dừng, rồi bật truy cập công khai
.\start-local.cmd
.\start-online.ps1

# Xem URL hiện tại, không in secret
python .\online.py status

# Dừng tunnel VÀ khôi phục cấu hình local
.\stop-online.ps1
```

Nếu chính sách PowerShell không cho chạy file, dùng `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\start-online.ps1` hoặc lệnh tương tự cho stop-online.ps1. Không thay đổi execution policy toàn hệ thống.

start-online hỏi trước khi công khai trong lần chạy thủ công; -ConfirmPublish chỉ bỏ qua câu hỏi khi đã chủ động cho phép. Bật lại khi hai tunnel/URL vẫn còn chạy sẽ tái sử dụng, không tạo trùng. Nếu phiên cũ đã dừng/đổi URL, script khôi phục rồi tạo lại. Không tự pull/nâng cloudflared; dùng image có sẵn. Hai container nền --restart=no nên không phụ thuộc terminal, nhưng không tự tiếp tục khi Docker/máy tắt.

Log trực tiếp: `docker logs --tail 80 cloud-storage-portal-tunnel` và `docker logs --tail 80 cloud-storage-nextcloud-tunnel`. Bản log lúc khởi tạo/dừng ở .online/cloud-storage-portal-tunnel.log và .online/cloud-storage-nextcloud-tunnel.log. Nhật ký Docker là nguồn cập nhật trong lúc chạy.

.online/state.json giữ URL và bản sao các khóa cấu hình địa chỉ Nextcloud ban đầu; .online/compose.json là override chỉ cho portal; .online/start-online.previous.ps1 giữ script cũ. Thư mục này được .gitignore bỏ qua. Không xóa .online khi còn chạy online vì cần state để khôi phục. File .env không bị sửa; snapshot hash đã đối chiếu không đổi. Không có token tunnel/tài khoản Cloudflare trong cấu hình mới.

### Cấu hình và khôi phục

Tunnel chạy trong mạng Docker, kết nối trực tiếp portal:8000 và nextcloud:80; không mở cổng modem. Portal chỉ đổi BASE_URL/NEXTCLOUD_PUBLIC_URL bằng Compose override và tin proxy đúng IP connector. Nextcloud thêm hostname công khai và trusted proxy đúng IP connector; overwritecondaddr giới hạn overwrite HTTPS theo connector để localhost:8080 vẫn chuyển hướng local đúng. Các khóa gốc được lưu và khôi phục bởi stop-online.

Khi bật online, portal đặt cookie Secure theo BASE_URL HTTPS: dùng URL công khai để đăng nhập. Đăng nhập portal/preview qua HTTP local có thể không giữ phiên; stop-online khôi phục portal local. Không chạy start-local khi đang muốn giữ online vì Compose base sẽ áp lại địa chỉ portal local; dừng online trước khi chuyển chế độ. Không chỉ dừng cloudflared rồi để nguyên cấu hình portal HTTPS.

### Bằng chứng kiểm tra và giới hạn

- Trang chủ/login/register/healthz CloudBox qua HTTPS trả 200, JS/CSS build hiện có tải được; các HTML công khai đã kiểm tra không có liên kết localhost. Địa chỉ kho trong bootstrap và biến runtime portal lấy URL Nextcloud mới.
- Nextcloud public root chuyển đến /login cùng hostname HTTPS, HTTP 200; CSS/JS trang đăng nhập tải qua tunnel. Local 8080 vẫn về http://localhost:8080/login.
- Health 8000/8001/8081/8026 và API Mailpit local đạt; hộp thư giữ 0 thư/0 chưa đọc. Không dùng tài khoản thật, không gửi email, không tạo đơn hoặc giao dịch để kiểm tra.
- Đã thử dừng: cấu hình Nextcloud so sánh đúng snapshot ban đầu, portal health đạt, Nextcloud local redirect đúng. Sau đó bật lại và kiểm tra URL mới; thao tác start lần nữa tái sử dụng phiên.
- Kết quả HTTP chi tiết ở .online/verification.json. Kiểm tra HTTPS thực hiện bằng HTTP client trên laptop; công cụ đọc web từ xa không truy cập được địa chỉ tạm, chưa xác minh bằng thiết bị khác/mạng 4G và chưa kiểm thử đăng nhập/upload/thanh toán end-to-end qua tunnel.
- Mailpit vẫn là hộp thư thử local; người đăng ký từ ngoài không tự nhận email trong hộp thư thật. Chưa đổi SMTP.
- Quick Tunnel không có địa chỉ cố định/bảo đảm uptime. Cần laptop bật, không Sleep, có Internet, Docker và hai container tunnel hoạt động; tạo lại có thể đổi URL khiến email/link/callback cũ không còn dùng được.
- Cloudflare Free giới hạn 100 MB cho mỗi HTTP request upload. Không tuyên bố tải 2 GB qua tunnel. Files 8081 hiện vẫn local; upload raw một request của bản đó sẽ cần chia nhỏ nếu công khai sau này. Chưa thử tệp lớn/chunk upload của Nextcloud qua tunnel.
- Đây là công khai hệ thống chạy trên laptop, chưa chuyển workload/dữ liệu lên VPS/cloud. Chưa mua domain, chưa tạo tài khoản Cloudflare hay dịch vụ trả phí, không thay dữ liệu/volumes.

Tham khảo: https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/ ; https://developers.cloudflare.com/support/troubleshooting/http-status-codes/4xx-client-error/error-413/ ; https://docs.nextcloud.com/server/stable/admin_manual/configuration_server/reverse_proxy_configuration.html


## 14. Thiết kế đồng bộ và hợp nhất UI — 31/10/2026

Đã đọc prompt thực thi, 4 mẫu Desktop, tài liệu/hệ thống và skills theo phạm vi. Đã đưa phương án kỹ thuật, tokens, bố cục và mockup trước khi sửa app. Không sửa mẫu Desktop/sources hoặc clone lại dự án thật.

- Cổng chính 8000 dùng React renderer tái sử dụng phần tốt của preview nhưng design system/bố cục/theme mới cho public/auth/dashboard/admin; giữ Python nghiệp vụ và pnpm lock. Bộ chuyển theme radio thật, keyboard, kính CSS tiết chế. Host Grotesk/Instrument Sans thiếu glyph Việt; đã kiểm cmap và chọn Be Vietnam Pro tự host/OFL cho toàn bộ chữ, báo rõ trước triển khai.
- 8080 giữ chính Nextcloud 35.0.2 và 51 app native; app cloudbox_theme dùng 2 public template events, CSS semantic/container, không JS/core/bundle patch, không tạo Nextcloud thứ hai. Primary color, nền cá nhân, native themes/high contrast/OpenDyslexic giữ chức năng. CSS có content hash và preset riêng cho nền cá nhân. Image Nextcloud pin đúng digest đang dùng.
- 8025 giữ toàn bộ native Vue UI + backend SMTP Mailpit v1.32.0; không promote gateway 8026 thiếu chức năng. Vendor source chính thức đúng tag, giữ cả lockfile/Go code, chỉ skin/component/UI build. Theme chung đồng bộ với mp-theme native, giữ Deep dark trong Settings. Mail được chuyển DB tạm sang volume persistent sau snapshot DB/WAL + SQLite backup/integrity. Đã đổi image native/custom để so sánh và chứng minh 2 thư QA không mất.
- Tài liệu design/function inventory/QA/rollback, ảnh trước-sau, provenance và script chạy cuối được cập nhật. start-local giữ override HTTPS khi đang online; không tự reset session/URL. Hai Quick Tunnel đang dùng được giữ, Mail không công khai.
- 76 Python + 10 mail client + 38 native Mailpit JS tests đạt. TypeScript/build/PHP syntax/core integrity đạt. 42 API checks thật và 30 responsive measurements đạt trong phạm vi ghi rõ; byte restore, PNG decode/PDF.js page 1, native themes/background được thử qua browser QA.

**Giới hạn nghiệm thu quan trọng:** Không gọi toàn hệ thống “hoàn tất không lỗi”. Native Nextcloud đóng viewer ghi setFullScreenMode error; đã tái hiện khi tắt theme. Sau restore một timestamp version cũ vẫn list nhưng GET404, giống hệt bật/tắt theme (byte file được restore đúng; version còn lại GET200). Mail có một lỗi MutationObserver trong trình duyệt tích hợp cần đối chiếu thêm; các tab và download vẫn hoạt động. Không vá/nâng lõi ngoài phạm vi. Xem UNIFIED-QA.md và UNIFIED-NATIVE-FINDINGS.json; các điểm này không được tính thành bài test pass.

Source/gateway/Dockerfile preview và image cũ được giữ để rollback, còn Compose hoạt động chỉ có db, redis, nextcloud, mailpit, portal. Các cổng thử chỉ được gỡ sau đối chiếu với chức năng bản chính; không xóa volume/tệp/thư/account thật. Trạng thái dọn QA, listeners, restart và public routes cuối được ghi ở UNIFIED-FINAL-VERIFICATION.json.

Chốt sau restart thật: scripts/verify-ui.py đạt; 5 dịch vụ healthy, chỉ 8000/8080/8025 mở và 3 cổng preview đóng; public HTTPS và 24 tài nguyên/font HTTP200, có một retry lỗi mạng tạm thời. Hai tài khoản/hai thư QA và credential tạm đã được dọn; counts về baseline. Xem UNIFIED-QA-CLEANUP.json, UNIFIED-FINAL-VERIFICATION.json và phần chốt sau restart trong UNIFIED-QA.md. Không thay đổi kết luận về lỗi native/giới hạn chưa kiểm tra.

## 15. Chẩn đoán ba vấn đề — 01/11/2026

> **Cập nhật 01/11/2026:** Kết luận phiên bản404 trước đây đã được hiệu chỉnh: bài thử gọi endpoint archive cho bản hiện tại; native dùng files DAV và tải đúng byte. Viewer đã có bản vá hai fallback Sidebar (17 test); app integrity sẽ báo đúng loader/module đã vá, core kiểm riêng. Lỗi MutationObserver tái hiện trên trang iframe không có Mailpit/JavaScript, thuộc lớp môi trường trình duyệt chưa xác định module cụ thể. Xem [chẩn đoán mới](DIAGNOSTICS-2026-11-01.md) và DIAGNOSTICS-FINAL.json. Các ghi nhận cũ phía dưới là lịch sử trước chẩn đoán.


Đã dùng một account Nextcloud/tệp và một thư Mailpit tạm riêng. Không đổi DB/business/retention, không nâng app, không đổi tunnel. Xem DIAGNOSTICS-2026-11-01.md; phần chốt/dọn QA ở DIAGNOSTICS-FINAL.json.
