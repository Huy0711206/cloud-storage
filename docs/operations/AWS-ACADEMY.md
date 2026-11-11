# Chạy và triển khai CloudBox trên AWS Academy

Website: **https://cloudbox.rachiba.top**. Máy phục vụ: **cloudbox-app-01**, vùng **us-east-1 — N. Virginia**. Ứng dụng và dữ liệu đang nằm trên EC2; laptop dùng để sửa mã nguồn.

## 1. Mở web để sử dụng hằng ngày

1. Đăng nhập [AWS Academy dành cho sinh viên](https://awsacademy.instructure.com/login/canvas).
2. Chọn **AWS Academy Lab Project – Cloud Web Application Builder** → **Modules** → **Lab Instructions: Building a Highly Available, Scalable Web Application**.
3. Bấm **Start Lab**, chờ trạng thái AWS màu xanh.
4. Nếu cần kiểm tra: bấm **AWS** → **EC2** → **Instances**; máy **cloudbox-app-01** cần ở trạng thái **Running** và hoàn tất kiểm tra trạng thái.
5. Chờ ứng dụng khởi động, rồi mở https://cloudbox.rachiba.top.

**Không cần mở Docker Desktop hoặc chạy start-local trên laptop.** Nếu phiên lab và web còn hoạt động, không cần Start Lab lại mỗi lần truy cập. Có thể tắt laptop mà web vẫn chạy khi EC2/lab còn hoạt động.

Docker Engine trên Ubuntu được thiết lập chạy khi máy khởi động; cả ba container dùng `restart: unless-stopped`. Nếu trước đó có người dừng container thủ công, hoặc dịch vụ khởi động lỗi, phải kiểm tra theo mục 4; không bảo đảm chỉ bấm Start Lab là hết mọi lỗi. Đây là cấu hình tự khởi động, chưa phải bằng chứng đã kiểm thử một vòng End Lab → Start Lab sau chuyển máy. [Docker trên Ubuntu](https://docs.docker.com/engine/install/linux-postinstall/), [quy tắc khởi động lại](https://docs.docker.com/engine/containers/start-containers-automatically/).

## 2. Docker đang làm gì?

| Thành phần | Giải thích | Nơi chạy |
|---|---|---|
| Docker Engine | Công cụ chạy các dịch vụ của website | EC2 Ubuntu |
| `portal` | Giao diện CloudBox và API xử lý nghiệp vụ | Container trên EC2 |
| `db` | PostgreSQL: tài khoản, gói, đơn hàng và thông tin tệp | Container trên EC2 |
| `tunnel` | Kết nối tên miền Cloudflare đến Portal | Container trên EC2 |
| Docker Desktop | Dùng khi lập trình hoặc đóng gói bản cập nhật | Laptop Windows |

**Image** là bản đóng gói ứng dụng; **container** là dịch vụ đang chạy từ image; **volume** là nơi giữ dữ liệu qua các lần thay container. **Compose** là tệp mô tả các dịch vụ, cấu hình và volume.

Hai tệp Compose đang dùng trên EC2:

- `/opt/cloudbox/compose.aws.yml`: `portal` và `db`.
- `/opt/cloudbox/compose.tunnel.yml`: `tunnel`.

Khi quản lý CloudBox trên EC2, dùng **cả hai** tệp trong lệnh Compose. Source của chúng ở [infrastructure/aws](../../infrastructure/aws/compose.aws.yml).

## 3. Kết nối vào EC2 bằng SSH

Chỉ cần bước này khi bảo trì, xử lý lỗi hoặc triển khai bản mới; không cần SSH mỗi lần mở web.

Trong AWS Console, mở máy `cloudbox-app-01` và lấy **Public IPv4 address hiện tại**. IP này có thể thay đổi sau khi máy dừng/bật lại. Chuẩn bị khóa `.pem` của lab; không gửi khóa vào chat hoặc Git.

**Chạy trên laptop, trong PowerShell.** Thay hai giá trị mẫu trước khi chạy:

```powershell
$Ec2Ip = 'IP_PUBLIC_HIEN_TAI'
$KeyFile = 'C:\duong-dan\vockey.pem'
ssh -o KexAlgorithms=curve25519-sha256 -o ConnectTimeout=10 -i $KeyFile "ubuntu@$Ec2Ip"
```

Khi SSH hỏi xác nhận máy chủ lần đầu, đối chiếu fingerprint với **EC2 → Actions → Monitor and troubleshoot → Get system log**. Không bỏ kiểm tra host key. Nếu báo `Connection timed out`, kiểm tra máy Running, IP EC2 và nguồn SSH của security group; hiện chỉ cho một IPv4 `/32` vào cổng 22. Đổi mạng/VPN có thể khiến IP laptop khác IP được phép.

## 4. EC2 đã Running nhưng web chưa lên

**Các lệnh Bash dưới đây chạy trên EC2, sau khi SSH**, không chạy trong PowerShell của laptop.

### Xem trạng thái

```bash
cd /opt/cloudbox
sudo systemctl is-active docker
sudo docker compose -f compose.aws.yml -f compose.tunnel.yml ps
```

Kết quả mong đợi: Docker báo `active`; `portal` và `db` báo `healthy`; `tunnel` báo `Up`. Nếu Docker chưa chạy:

```bash
sudo systemctl start docker
```

### Bật lại các dịch vụ đã có

```bash
cd /opt/cloudbox
sudo docker compose -f compose.aws.yml -f compose.tunnel.yml up -d --wait
```

Lệnh này dùng cấu hình và volume hiện có, không phải cài lại database. Nếu báo thiếu volume hoặc thiếu config, dừng để kiểm tra; không tự tạo volume trống thay thế.

### Kiểm tra ứng dụng và tunnel

```bash
curl -fsS http://127.0.0.1:8000/healthz
curl -fsS http://127.0.0.1:20241/ready
```

Ứng dụng cần trả `{"status":"ok"}`; tunnel cần trả trạng thái sẵn sàng. Sau đó mở web bằng tên miền HTTPS. Nếu vẫn lỗi, xem phần log cuối:

```bash
sudo docker compose -f compose.aws.yml -f compose.tunnel.yml logs --tail 50 portal
sudo docker compose -f compose.aws.yml -f compose.tunnel.yml logs --tail 30 tunnel
```

Chỉ chia sẻ phần lỗi cần thiết, che thông tin riêng. Không in/gửi toàn bộ config. Không tạo tunnel hay tên miền khác để chữa lỗi khởi động.

## 5. Triển khai bản cập nhật sau khi sửa mã nguồn

**Chỉ thực hiện khi muốn cập nhật ứng dụng. Mở web hằng ngày hoặc chỉ sửa README thì không làm phần này.** Sửa mã trên laptop không tự thay website AWS.

Quy trình: **kiểm thử → build image trên laptop → chuyển image → nạp trên EC2 → thay riêng Portal → kiểm tra web**. Giữ nguyên database, kho tệp, tunnel và private config. Với thay đổi schema/database, cần kế hoạch migration riêng; quy trình này không thay thế kế hoạch đó.

### Bước 1 — Kiểm thử trên laptop

Làm theo [hướng dẫn phát triển](../development/DEVELOPMENT.md): frontend `pnpm check`/`pnpm build`, backend chạy các kiểm thử liên quan bằng dữ liệu riêng. Không dùng database production hoặc Gmail/thanh toán thật làm dữ liệu QA.

### Bước 2 — Đóng gói trên laptop

Lúc này mới cần mở Docker Desktop. Trong PowerShell, tại **thư mục gốc dự án**:

```powershell
docker build --platform linux/amd64 -t cloudbox-portal:release-01 ./apps/portal
```

Chỉ tiếp tục khi build thành công:

```powershell
docker save -o .\cloudbox-release.tar cloudbox-portal:release-01
Get-FileHash -LiteralPath .\cloudbox-release.tar -Algorithm SHA256
```

`release-01` là ví dụ: dùng tên phiên bản mới cho mỗi lần phát hành. `linux/amd64` khớp kiến trúc EC2 hiện tại. Image chứa ứng dụng, không chứa dữ liệu trong volume hoặc thay thế private config. Requirements Python chưa khóa tuyệt đối nên build mới có thể lấy phiên bản thư viện khác; cần kiểm thử chính image dự định phát hành trong môi trường QA trước khi dùng production.

### Bước 3 — Chuyển image từ laptop

Trong **PowerShell**, đặt `$Ec2Ip` và `$KeyFile` như mục 3 rồi chạy:

```powershell
scp -o KexAlgorithms=curve25519-sha256 -i $KeyFile .\cloudbox-release.tar "ubuntu@${Ec2Ip}:/home/ubuntu/"
```

Chỉ chuyển image. Không chép database laptop, volume cũ hoặc `.env` laptop đè lên AWS.

### Bước 4 — Nạp image trên EC2

SSH vào EC2. **Chạy Bash trên EC2**:

```bash
sha256sum /home/ubuntu/cloudbox-release.tar
```

Đối chiếu chuỗi SHA-256 với kết quả trên laptop. Nếu khác, không nạp; chuyển lại tệp. Khi khớp:

```bash
sudo docker inspect --format '{{.Image}}' cloud-storage-portal-1
sudo docker load -i /home/ubuntu/cloudbox-release.tar
sudo docker tag cloudbox-portal:release-01 cloud-storage-portal:native
```

Ghi lại ID image cũ từ lệnh `inspect`, giữ image cũ để có thể quay lại mã khi phù hợp. `tag` chỉ đặt tên mà Compose hiện dùng cho image mới; không tự thay container đang chạy.

### Bước 5 — Cập nhật riêng Portal trên EC2

```bash
cd /opt/cloudbox
sudo docker compose -f compose.aws.yml -f compose.tunnel.yml config -q
```

Nếu cấu hình hợp lệ, chạy:

```bash
sudo docker compose -f compose.aws.yml -f compose.tunnel.yml up -d --no-deps --force-recreate --wait portal
```

Website có thể gián đoạn ngắn khi thay Portal. Không chạy `down -v`, không tạo database mới và không recreate `db`/`tunnel` chỉ để cập nhật giao diện hoặc API.

### Bước 6 — Xác nhận bản mới

Chạy các lệnh kiểm tra ở mục 4, rồi thử đăng nhập, mở kho, tải lên/tải xuống một tệp nhỏ, kiểm quota và nội dung vừa sửa. Chỉ kết luận triển khai thành công khi các kiểm tra đạt. Nếu chỉ thay mã và chưa thay dữ liệu/schema, có thể đánh giá quay lại image cũ; nếu đã có migration thì phải kiểm tính tương thích trước.

## 6. Chỉnh email hoặc cấu hình ứng dụng

Website AWS đọc **`/opt/cloudbox/private/portal.env`**. Sửa `.env` trên laptop **không cập nhật** website AWS. Người dùng chỉnh trực tiếp trên EC2 bằng trình soạn thảo, giữ quyền tệp 600.

Ví dụ Gmail trong `portal.env`: `SMTP_HOST=smtp.gmail.com`, `SMTP_PORT=587`, `SMTP_STARTTLS=true`; `SMTP_USER` và `MAIL_FROM` là Gmail gửi, `SMTP_PASSWORD` là Google App Password. Không dùng mật khẩu Gmail thông thường. Xem [tạo App Password](https://support.google.com/accounts/answer/185833?hl=vi).

Sau khi lưu, dùng lệnh **cập nhật riêng Portal ở bước 5** để nạp config mới. Không build image chỉ vì sửa config. Giữ `SECRET_KEY` nếu muốn giữ phiên đăng nhập. Sửa mật khẩu trong `db.env` không tự đổi mật khẩu role PostgreSQL đã tồn tại; không làm việc đó như một cách sửa lỗi đăng nhập CloudBox.

## 7. Triển khai lên một máy chủ mới khác

Đây là chuyển môi trường, **không phải bước lặp lại mỗi lần Start Lab**:

1. Chuẩn bị máy Ubuntu/Docker và đủ dung lượng; tạo thư mục `/opt/cloudbox`.
2. Đưa [compose.aws.yml](../../infrastructure/aws/compose.aws.yml) và [compose.tunnel.yml](../../infrastructure/aws/compose.tunnel.yml) tới đó. Người dùng nhập private config và cấp tunnel token cho đúng máy; không đưa secrets vào Git.
3. Chuẩn bị image đã QA và đích dữ liệu mới được xác minh trống.
4. Chốt ngừng ghi nguồn, chuyển database **và** kho tệp cùng thời điểm. Giữ ID, password hash, quota, đơn hàng, phiên bản và các liên kết.
5. So sánh đầy đủ metadata/checksum, kiểm health và luồng người dùng rồi mới chuyển đích tên miền.
6. Giữ dữ liệu nguồn theo phương án phục hồi đã thống nhất; không để hai bản database cùng nhận ghi cho một website.

Không dùng dữ liệu laptop tại lần chuyển 10/11 để ghi đè AWS: dữ liệu AWS đã có thể phát sinh mới. Chi tiết/bằng chứng lần chuyển: [báo cáo QA](../../artifacts/qa/aws-deployment-2026-11-10.md).

## 8. Dừng lab, chi phí và dữ liệu cần giữ

- Kết thúc sử dụng: bấm **End Lab** và xác nhận. Đóng tab trình duyệt hoặc tắt laptop không phải dừng lab. **Không bấm Reset**.
- Start Lab có thể bật lại cả các máy bài tập khác; chúng dùng chung ngân sách. Máy chạy tính phí thời gian, ổ EBS vẫn tính phí khi còn lưu dữ liệu. Số liệu ngân sách có thể cập nhật chậm; Academy không phải hosting miễn phí vô hạn/24 giờ mỗi ngày.
- Cấu hình đã triển khai: Ubuntu 24.04, t3.small, CPU Standard; EBS gp3 40 GiB mã hóa, không tự xóa ổ khi terminate. Đây là cấu hình khởi đầu, không phải mức tối đa của Academy.
- Volume trên EC2: `cloud-storage_db_data` và `cloud-storage_cloudbox_data`; Compose project `cloud-storage`. Tên giống volume laptop nhưng nằm trên máy khác.
- Giữ `/opt/cloudbox/private/`, database, volume và dữ liệu nguồn. Không `down -v`, prune volume, `remove-orphans`, tạo volume rỗng thay kho hoặc Reset lab để xử lý lỗi.
- Hạn mức gói 5/100/500/2048 GiB là quota; toàn hệ thống đang có **pool thử nghiệm 20 GiB**, không phải đã mua ổ 2 TB.
- Chưa thiết lập sao lưu dài hạn. Khi lab hết ngân sách/khóa học hết hạn, dữ liệu không được bảo đảm còn. Quay lại máy cũ sau khi AWS đã nhận dữ liệu mới cần quy trình chuyển ngược và kiểm chứng, không chỉ đổi DNS.
