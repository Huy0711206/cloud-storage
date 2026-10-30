# CloudBox — Cloud Data Storage

CloudBox gồm cổng dịch vụ do nhóm phát triển và kho quản lý tệp Nextcloud. Cổng dùng React, TypeScript, Tailwind CSS, shadcn/ui và FastAPI. PostgreSQL lưu tài khoản, gói dịch vụ và đơn hàng; Redis hỗ trợ Nextcloud; Mailpit nhận email thử nghiệm; CloudBox Mail là giao diện hộp thư mới ở cổng 8026, dùng cùng dữ liệu Mailpit.

## 1. Chạy hệ thống trong VS Code

### 1.1. Khởi động hằng ngày

Máy đã có Docker Desktop, WSL 2 và file `.env` được cấu hình. Mỗi lần sử dụng, thực hiện như sau:

1. Trong VS Code, chọn **File → Open Folder** và mở thư mục `cloud-storage` chứa README này. Thư mục gốc phải có `docker-compose.yml`, `start-local.cmd` và `.env`.
2. Chọn **Terminal → New Terminal**, sử dụng terminal **PowerShell**.
3. Tại thư mục gốc dự án, chạy:

~~~powershell
.\start-local.cmd
~~~

Nếu terminal đang ở thư mục khác, chuyển đến vị trí dự án trên laptop này trước:

~~~powershell
Set-Location -LiteralPath 'C:\Users\jnguyen\Downloads\ĐH Mở\DTDM\Bai Tap Lon\cloud-storage'
.\start-local.cmd
~~~

Tệp khởi động sẽ thực hiện lần lượt:

- Kiểm tra Docker Desktop, mở Docker nếu chưa chạy và đợi Docker sẵn sàng.
- Khởi động PostgreSQL, Redis, Nextcloud, Mailpit, portal chính, giao diện portal thử nghiệm và CloudBox Mail; đợi các dịch vụ báo sẵn sàng.
- Kiểm tra các cổng CloudBox, hộp thư 8025/8026 và trang đăng nhập Nextcloud ở cổng 8080, sau đó mở trình duyệt tại **http://localhost:8000**.

Khi thành công, terminal sẽ có các dòng:

~~~text
OK: http://localhost:8000
OK: http://localhost:8001
OK: http://localhost:8026
OK: http://localhost:8025 (Mailpit gốc)
OK: http://localhost:8080 (Nextcloud)
~~~

**Giữ Docker Desktop chạy trong lúc dùng ứng dụng.** Sau khi lệnh hoàn tất thành công, có thể đóng terminal; các container tiếp tục chạy ở chế độ nền. Nếu Docker yêu cầu xử lý WSL hoặc khởi động lại Windows, hoàn tất yêu cầu đó rồi chạy lại lệnh trên.

### 1.2. Lần đầu build hoặc sau khi sửa mã nguồn

Khi chưa có image của portal, hoặc sau khi thay đổi frontend/backend, chạy từ thư mục gốc:

~~~powershell
.\start-local.cmd -Rebuild
~~~

`-Rebuild` giữ nguyên chức năng build lại image `portal` gồm React và FastAPI ở cổng chính **8000**, sau đó khởi động và kiểm tra toàn bộ hệ thống như mục 1.1. Cần Internet nếu Docker phải tải image hoặc thư viện chưa có.

Để cập nhật **chỉ giao diện thiết kế thử nghiệm ở cổng 8001**, chạy:

~~~powershell
.\start-local.cmd -RebuildPreview
~~~

`-RebuildPreview` chỉ build image `portal-preview`, không build lại image `portal`. Sau đó script vẫn khởi động và kiểm tra cả hai địa chỉ. Mở http://localhost:8001 để xem thiết kế mới; http://localhost:8000 là giao diện chính ổn định. Khi sửa cả bản chính lẫn bản thử nghiệm, có thể dùng `.\start-local.cmd -Rebuild -RebuildPreview`.

Để cập nhật **chỉ giao diện hộp thư mới ở cổng 8026**, chạy:

~~~powershell
.\start-local.cmd -RebuildMail
~~~

`-RebuildMail` chỉ build service `mail-preview`. Cờ này không build lại `portal`, `portal-preview` hoặc image Mailpit gốc. Mở http://localhost:8026 để dùng giao diện mới; http://localhost:8025 vẫn là giao diện Mailpit gốc. Có thể kết hợp các cờ build khi thực sự sửa nhiều phần.

Hai giao diện dùng chung backend, tài khoản, database và kho Nextcloud. Các thao tác đăng ký, đổi mật khẩu, chọn gói hoặc thanh toán ở 8001 tác động lên dữ liệu chung; đây không phải môi trường dữ liệu thử riêng. Email và thanh toán vẫn dùng địa chỉ chuẩn `BASE_URL` của backend.

**Khởi động hằng ngày dùng `.\start-local.cmd`; chỉ thêm cờ build khi cần tạo lại image tương ứng.** Không cần chạy thêm `uvicorn`, `pnpm dev` hoặc máy chủ cổng 8002 khi sử dụng hệ thống bằng Docker.

Nếu cài sang một máy mới chưa có `.env`, thực hiện phần cấu hình ở mục 4 trước.

### 1.3. Các địa chỉ sau khi khởi động

| Địa chỉ | Mục đích |
|---|---|
| http://localhost:8000 | CloudBox — cổng chính |
| http://localhost:8001 | CloudBox — giao diện thiết kế thử nghiệm |
| http://localhost:8080 | Nextcloud — quản lý tệp |
| http://localhost:8025 | Mailpit — giao diện hộp thư gốc |
| http://localhost:8026 | CloudBox Mail — giao diện hộp thư thử nghiệm mới |

Cổng 8000 phục vụ bản chính; cổng 8001 phục vụ giao diện thử nghiệm và chuyển các yêu cầu nghiệp vụ về cùng backend. Giải thích chi tiết nằm ở mục 2.

### 1.4. Chạy không cần mở VS Code

Mở thư mục dự án bằng File Explorer và nhấp đúp `start-local.cmd`. Quy trình khởi động giống mục 1.1.

Nếu muốn chạy trực tiếp bằng Docker, mở Docker Desktop, đợi Docker sẵn sàng, rồi chạy lệnh sau **tại thư mục gốc dự án**:

~~~powershell
docker compose up -d --wait --wait-timeout 180
~~~

Sau khi lệnh thành công, tự mở http://localhost:8000. Lệnh Docker trực tiếp không tự mở Docker Desktop hoặc trình duyệt.

## 2. Các cổng và ý nghĩa

| Địa chỉ/cổng | Vai trò hiện tại |
|---|---|
| http://localhost:8000 | **Cổng chính của CloudBox** |
| http://localhost:8001 | **Giao diện thử nghiệm CloudBox (portal-preview)** |
| 8002 | Đã ngừng sử dụng; trước đây chỉ là môi trường kiểm thử tạm |
| http://localhost:8080 | Giao diện kho tệp Nextcloud |
| http://localhost:8025 | Mailpit — giao diện hộp thư gốc |
| http://localhost:8026 | CloudBox Mail — giao diện mới (mail-preview) |
| PostgreSQL 5432 | Chỉ dùng trong mạng Docker, không mở ra laptop |

Cấu hình hiện tại công bố **127.0.0.1:8000 → portal:8000** cho bản chính và **127.0.0.1:8001 → portal-preview:8000** cho bản thiết kế thử nghiệm. Cổng 8000 bên trong mỗi container là nơi dịch vụ của container đó lắng nghe; số bên trái là cổng bạn mở trên laptop.

`portal-preview` phục vụ bộ giao diện mới và chuyển yêu cầu nghiệp vụ đến `portal`. Hai địa chỉ dùng chung backend, database và tài khoản. Giao diện ở 8001 không có database hoặc tác vụ bảo trì riêng, và **không phải máy chủ dự phòng độc lập**. Nếu backend hoặc database bị lỗi thì cả hai địa chỉ cùng bị ảnh hưởng. Nếu phần mềm khác chiếm một trong hai cổng lúc khởi động, Docker sẽ báo lỗi; cần giải phóng cổng đó hoặc điều chỉnh ánh xạ.

BASE_URL=http://localhost:8000 là địa chỉ chuẩn để tạo liên kết xác thực email và URL quay về sau thanh toán. Các email cũ có thể còn liên kết tới 8001; địa chỉ đó vẫn chuyển yêu cầu đến cùng backend. Không có tunnel nào được tự bật khi chạy start-local.

### Hộp thư 8025 và 8026

`127.0.0.1:8026` phục vụ ứng dụng React CloudBox Mail qua service `mail-preview`. Các yêu cầu API được chuyển tiếp trong mạng Docker tới Mailpit hiện có. Giao diện này không có kho thư hay SMTP riêng; cấu hình gửi email của CloudBox và mẫu email xác thực giữ nguyên.

**8025 và 8026 dùng chung hộp thư.** Đọc thư có thể đánh dấu đã đọc; đánh dấu hoặc xóa thư ở một giao diện sẽ ảnh hưởng dữ liệu nhìn thấy ở giao diện còn lại. 8026 là bản thử giao diện, không phải môi trường dữ liệu độc lập hoặc máy chủ thư dự phòng.

Chỉ build/khởi động lại phần hộp thư mới khi đang phát triển:

~~~powershell
docker compose build mail-preview
docker compose up -d --no-deps --wait mail-preview
~~~

Dừng riêng giao diện mới bằng `docker compose stop mail-preview`; Mailpit 8025 tiếp tục hoạt động. Chạy lại bằng `docker compose up -d --no-deps --wait mail-preview`. Không cần bật tunnel, đổi SMTP hoặc tạo tài khoản mới để xem thư.

## 3. Kiến trúc và chức năng

~~~text
Trình duyệt → localhost:8000 → React bản chính + FastAPI portal
                    ↑
Trình duyệt → localhost:8001 → portal-preview (React mới + chuyển tiếp yêu cầu)

            FastAPI portal dùng chung:
               ├─ PostgreSQL / portal: users, plans, orders
               ├─ Email SMTP → Mailpit
               ├─ VNPay: tạo đơn, Return URL, IPN, kiểm tra chữ ký
               └─ Nextcloud API: tạo tài khoản, hạn mức, khóa/mở

Trình duyệt → localhost:8080 → Nextcloud
                                ├─ PostgreSQL / nextcloud
                                ├─ Redis
                                └─ Volume chứa tệp người dùng
~~~

- Đăng ký tạo tài khoản Nextcloud đang khóa; xác thực email sẽ kích hoạt kho.
- Đăng nhập CloudBox và Nextcloud bằng cùng email, mật khẩu.
- Dashboard hiển thị dung lượng, gói đang dùng, lịch sử đơn và đổi mật khẩu.
- Mua/gia hạn gói qua VNPay; backend kiểm tra chữ ký, số tiền và cập nhật hạn mức.
- Tác vụ bảo trì hạ tài khoản hết hạn về gói miễn phí và thử lại hạn mức chưa đồng bộ.
- Quản trị có thống kê, tìm người dùng, khóa/mở, cấp gói, sửa gói và xem đơn hàng.
- Giao diện CloudBox hỗ trợ sáng/tối, mobile, tablet, bàn phím và các trạng thái tải/rỗng/lỗi.
- Nextcloud cung cấp giao diện quản lý tệp riêng.

Gói mặc định: Miễn phí 5 GB; Cơ bản 100 GB — 25.000 ₫/tháng; Tiêu chuẩn 500 GB — 69.000 ₫/tháng; Cao cấp 2 TB — 199.000 ₫/tháng. Mua 12 tháng thanh toán 10 tháng. Giá thực tế lấy từ database và có thể sửa trong trang quản trị.

## 4. Cấu hình khi cài máy mới hoặc thay đổi .env

Dự án trên laptop hiện đã có dữ liệu và `.env`. Khi chỉ mở lại ứng dụng, dùng mục 1.1; giữ file cấu hình và các volume hiện tại.

Khi cài một bản mới trên máy khác:

1. Cài Docker Desktop, thiết lập WSL 2 theo hướng dẫn của Docker và mở thư mục gốc dự án.
2. Chỉ tạo `.env` từ mẫu nếu tệp chưa tồn tại:

~~~powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
~~~

3. Điền thông tin database, tài khoản quản trị, email và thanh toán của môi trường mới trong `.env`. Địa chỉ CloudBox cục bộ là `BASE_URL=http://localhost:8000`.
4. Chạy `.\start-local.cmd -Rebuild` theo mục 1.2.

Docker tự build React và FastAPI; Windows không cần cài Node hoặc Python riêng để chạy ứng dụng bằng Docker.

Để áp dụng thay đổi `.env` mà không sửa code, mở Docker Desktop và chạy từ thư mục gốc:

~~~powershell
docker compose up -d --wait --wait-timeout 180
~~~

**`POSTGRES_PASSWORD` chỉ được dùng để đặt mật khẩu PostgreSQL khi khởi tạo dữ liệu lần đầu.** Sửa giá trị này trong `.env` không tự đổi mật khẩu tài khoản đã lưu trong database. Nếu hai phía không khớp, portal có thể báo `password authentication failed` và khởi động lại liên tục. Cần cập nhật tài khoản PostgreSQL và cấu hình kết nối đồng bộ; giữ volume khi xử lý lỗi kết nối.

Tương tự, tài khoản Nextcloud đã cài không tự đổi mật khẩu khi sửa `NEXTCLOUD_ADMIN_PASSWORD` trong `.env`. Cấu hình này cũng được portal dùng để gọi API quản trị Nextcloud, nên phải khớp tài khoản đang có trong kho.

## 5. Dừng và xem trạng thái

Chạy các lệnh sau trong terminal PowerShell tại thư mục gốc dự án:

~~~powershell
# Trạng thái và kiểm tra sức khỏe dịch vụ
docker compose ps

# Xem log gần nhất
docker compose logs --tail 60 portal portal-preview mail-preview mailpit nextcloud db

# Tạm dừng, giữ container và dữ liệu
docker compose stop

# Chạy lại sau khi dừng
.\start-local.cmd
~~~

docker compose down xóa các container và mạng của dự án, vẫn giữ volume dữ liệu. **Không thêm -v nếu muốn giữ tài khoản và tệp.**

## 6. Xử lý khi không mở được web

| Hiện tượng | Cách xử lý |
|---|---|
| Cannot connect to Docker / Docker chưa sẵn sàng | Chạy start-local.cmd; nếu vẫn lỗi, mở Docker Desktop xem trạng thái WSL và thông báo của Docker |
| Portal ở trạng thái Restarting | Xem log portal. Nếu có password authentication failed thì cấu hình kết nối không khớp mật khẩu trong PostgreSQL; đổi cổng không xử lý được lỗi này |
| Address already in use / port is already allocated | Kiểm tra tiến trình hoặc container đang giữ 8000/8001/8025/8026; không tắt nhầm ứng dụng khác |
| Portal unhealthy | Xem log portal và db; kiểm tra /healthz. Script khởi động đợi dịch vụ sẵn sàng thay vì mở trình duyệt ngay |
| Chỉ cổng 8001 không mở được | Xem docker compose ps và log portal-preview; dịch vụ này cần portal chính hoạt động. Nếu vừa sửa giao diện, chạy start-local.cmd -RebuildPreview |
| Chỉ cổng 8026 không mở được | Xem log mail-preview, kiểm tra Mailpit 8025 còn chạy; sau khi sửa giao diện chạy start-local.cmd -RebuildMail |
| 8026 không thấy thư hoặc báo lỗi kết nối | So sánh danh sách tại 8025; hai giao diện dùng cùng hộp thư. Kiểm tra service mailpit và log mail-preview, sau đó dùng nút làm mới |
| Nextcloud chưa sẵn sàng | Chờ cài đặt hoàn tất và xem log nextcloud. Khi chạy lần đầu có thể mất vài phút |
| Trang vẫn là giao diện cũ | Cổng 8001: chạy start-local.cmd -RebuildPreview; cổng 8000: chạy start-local.cmd -Rebuild. Sau đó tải lại trình duyệt |
| Không thấy email xác thực | Mở http://localhost:8026 hoặc http://localhost:8025; xem email mới nhất thay vì dùng liên kết tunnel cũ |
| Email/thanh toán quay về địa chỉ cũ | Đặt BASE_URL=http://localhost:8000 trong .env, áp dụng lại cấu hình và yêu cầu email xác thực mới |
| Đăng ký/đồng bộ báo Unauthorised từ Nextcloud | Kiểm tra NEXTCLOUD_ADMIN_USER và NEXTCLOUD_ADMIN_PASSWORD khớp tài khoản quản trị đang có trong Nextcloud; sửa .env không tự đổi mật khẩu bên trong Nextcloud |
| Mở 8080 nhưng bị chuyển sang localhost/login hoặc cổng 80 | overwritehost bị thiếu cổng. Đặt thành localhost:8080 bằng lệnh bên dưới; khi chạy cục bộ dùng http://localhost:8080 |
| Nextcloud báo tên miền không tin cậy | Khi dùng localhost hãy giữ localhost trong trusted domains; khi đổi sang máy chủ/tên miền khác cần cấu hình lại Nextcloud |

Nếu Nextcloud chuyển hướng nhầm sang cổng 80, chạy từ thư mục gốc:

~~~powershell
docker compose exec -T -u www-data nextcloud php occ config:system:set overwritehost --value=localhost:8080
~~~

Sau đó mở lại http://localhost:8080. Cấu hình này được lưu trong volume Nextcloud; nếu sau này dùng tên miền công khai, cần đổi theo địa chỉ triển khai đó.

Kiểm tra cổng trên Windows:

~~~powershell
Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
    Where-Object { $_.LocalPort -in 8000,8001,8002,8025,8026 } |
    Select-Object LocalAddress,LocalPort,OwningProcess

docker ps --format '{{.Names}}: {{.Ports}}'
~~~

Cổng không có tiến trình lắng nghe nghĩa là chưa có dịch vụ mở cổng đó; không phải lúc nào cũng là xung đột cổng.

## 7. Xem database

PostgreSQL nằm trong service db, dữ liệu lưu ở volume db_data. Có hai database portal và nextcloud. Tệp tải lên được lưu ở volume nextcloud_data, không phải trong bảng users/orders.

Mở terminal của container db trong Docker Desktop và chạy:

~~~sh
psql -U "$POSTGRES_USER" -d portal
~~~

Sau đó:

~~~sql
\dt
SELECT id, full_name, email, is_verified FROM users;
SELECT * FROM plans;
SELECT * FROM orders;
\q
~~~

Không sửa/xóa trực tiếp các bảng nội bộ Nextcloud khi chưa hiểu quan hệ dữ liệu.

## 8. Email và VNPay khi demo

Mặc định Mailpit nhận email thử nghiệm; xem bằng CloudBox Mail tại http://localhost:8026 hoặc giao diện Mailpit gốc tại http://localhost:8025. Muốn gửi ra email thật cần cấu hình SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_STARTTLS và MAIL_FROM rồi áp dụng lại .env.

VNPay cần cấu hình merchant sandbox hợp lệ: VNPAY_TMN_CODE, VNPAY_HASH_SECRET, VNPAY_PAY_URL. Dùng thông tin thẻ thử nghiệm trong tài liệu sandbox của VNPay. Địa chỉ quay về hiện tại là:

~~~text
http://localhost:8000/billing/vnpay/return
~~~

IPN cần địa chỉ công khai mà VNPay truy cập được. Chạy localhost trên laptop chưa đáp ứng phần IPN công khai. start-online.ps1 là helper tunnel thử nghiệm cũ, không phải tệp khởi động hằng ngày và không được start-local tự gọi.

## 9. Cấu trúc mã nguồn và kiểm thử

~~~text
cloud-storage/
├─ start-local.cmd / start-local.ps1   # khởi động hằng ngày
├─ docker-compose.yml                 # dịch vụ, cổng, healthcheck
├─ .env.example                       # cấu hình mẫu, không ghi đè .env
├─ db-init/                           # tạo database portal lần đầu
└─ portal/
   ├─ Dockerfile                      # build React bản chính, chạy FastAPI
   ├─ Dockerfile.preview / preview.py # build UI thử nghiệm, chuyển tiếp về portal
   ├─ Dockerfile.mail-preview / mail_gateway.py # UI hộp thư, API tới Mailpit
   ├─ frontend/
   │  ├─ src/                         # React + TypeScript + shadcn/ui; mail/ là hộp thư riêng
   │  ├─ DESIGN.md                    # design system
   │  └─ QA.md                        # kết quả kiểm thử giao diện
   ├─ app/
   │  ├─ main.py / config.py / db.py
   │  ├─ frontend.py                  # dữ liệu công khai cho React
   │  ├─ models.py / services.py
   │  ├─ routers/                     # auth, dashboard, billing, admin
   │  ├─ security.py / nextcloud.py / vnpay.py
   │  └─ templates/ / static/
   └─ tests/                          # kiểm thử nghiệp vụ và bootstrap
~~~

Kết quả kiểm thử giao diện mới ở cổng 8001: [PREVIEW-QA.md](portal/frontend/PREVIEW-QA.md).

Giao diện hộp thư mới ở cổng 8026: [MAIL-DESIGN.md](portal/frontend/MAIL-DESIGN.md) mô tả thiết kế và kết nối; [MAIL-QA.md](portal/frontend/MAIL-QA.md) ghi nhận kiểm thử thực tế và giới hạn.

Kiểm thử độc lập dùng SQLite tạm và Nextcloud giả:

~~~powershell
Set-Location portal
python -m pip install -r requirements.txt pytest
python -m pytest -q
~~~

Frontend, nếu phát triển bằng Node + pnpm:

~~~powershell
Set-Location portal/frontend
pnpm install --frozen-lockfile
pnpm build
~~~

CloudBox Mail được build riêng bằng `pnpm exec vite build --config vite.mail.config.ts`, xuất ra `dist-mail`; Docker dùng `Dockerfile.mail-preview`. Khi chỉnh TypeScript, chạy `pnpm check` trước khi build.

Bản chính được phục vụ ở cổng 8000; bản thiết kế thử nghiệm ở 8001 dùng cùng backend. Dockerfile.preview chọn giao diện mới bằng VITE_UI_VARIANT=preview; không cần chạy thêm máy chủ 8002.

## 10. Giới hạn hiện tại

- Bản chính 8000 và giao diện thử nghiệm 8001 dùng chung backend và database, chưa có dự phòng máy chủ độc lập.
- Hộp thư 8025/8026 dùng cùng dữ liệu Mailpit; 8026 không phải hộp thư riêng hoặc ứng dụng gửi thư ra Internet.
- Đổi sang gói khác tính thời hạn từ hôm nay, chưa quy đổi phần thời gian còn lại.
- Chưa có quên mật khẩu qua email, CSRF token riêng, giới hạn đăng nhập sai, hóa đơn VAT, hoàn tiền hay thanh toán tự động định kỳ.
- Demo đang dùng HTTP cục bộ; triển khai Internet cần thiết kế hosting, HTTPS và cấu hình callback phù hợp.
- Portal và Nextcloud dùng cùng thông tin đăng nhập nhưng chưa có SSO tự đăng nhập giữa hai giao diện.

## 11. Kết quả sửa và kiểm tra ngày 30/10/2026

Các kết quả dưới đây ghi nhận đợt khắc phục kết nối trước khi tách giao diện thử nghiệm. Cấu hình chạy hiện tại của 8000/8001 được mô tả ở mục 1–2.

- Nguyên nhân web không mở: portal bị lặp khởi động vì mật khẩu tài khoản PostgreSQL cloud không khớp cấu hình. Đã đồng bộ tài khoản kết nối với cấu hình hiện tại, giữ dữ liệu.
- Phát hiện thêm mật khẩu quản trị Nextcloud không khớp .env; đã đồng bộ theo lựa chọn của người dùng và xác minh API CloudBox → Nextcloud hoạt động. Mật khẩu đăng nhập quản trị Nextcloud hiện lấy theo NEXTCLOUD_ADMIN_PASSWORD trong .env; cổng quản trị CloudBox dùng ADMIN_EMAIL / ADMIN_PASSWORD riêng.
- Cổng 8000 chính và 8001 dự phòng cùng phục vụ portal; 8002 không còn dịch vụ lắng nghe.
- Đã thử dừng và chạy lại toàn bộ dịch vụ bằng start-local.ps1, không build lại; cả năm dịch vụ healthy, số bản ghi users/plans/orders giữ nguyên.
- Trang chủ, đăng nhập, đăng ký và /healthz đều trả HTTP 200 trên cả hai cổng.
- Build React/TypeScript thành công; 19 kiểm thử nghiệp vụ/bootstrap đạt trong môi trường tạm riêng.

- Bổ sung kiểm tra 8080: đã sửa overwritehost từ localhost thành localhost:8080. Trang chủ Nextcloud hiện chuyển về http://localhost:8080/login và trả HTTP 200; start-local cũng kiểm tra trang này khi khởi động.
