# CloudBox

CloudBox là website lưu trữ tệp, quản lý tài khoản và gói dịch vụ tại **https://cloudbox.rachiba.top**. Website hiện chạy trên **AWS Academy EC2**, không còn phục vụ từ laptop.

## 1. Muốn mở web thì làm gì?

1. Vào [AWS Academy sinh viên](https://awsacademy.instructure.com/login/canvas).
2. Chọn **AWS Academy Lab Project – Cloud Web Application Builder** → **Modules** → **Lab Instructions: Building a Highly Available, Scalable Web Application**.
3. Bấm **Start Lab**, chờ AWS màu xanh và máy **cloudbox-app-01** khởi động xong.
4. Mở **https://cloudbox.rachiba.top**.

**Không cần bật Docker Desktop trên laptop.** Nếu phiên lab vẫn hoạt động và web đã lên, chỉ cần mở tên miền; không Start Lab lại mỗi lần truy cập. Website tiếp tục chạy khi tắt laptop nếu EC2 và lab còn hoạt động.

Các dịch vụ trên EC2 đã cấu hình tự khởi động. Nếu container từng bị dừng thủ công hoặc khởi động lỗi, làm theo mục 3. Đây không phải cam kết mọi lần bật lab đều thành công mà không cần kiểm tra.

Khi kết thúc sử dụng, bấm **End Lab** để kết thúc phiên. Đóng tab hoặc tắt laptop không phải dừng lab. **Không bấm Reset**. Start Lab có thể bật lại cả các máy bài tập khác và dùng chung ngân sách; ổ đĩa vẫn có thể tính phí khi máy dừng. Academy có giới hạn phiên/ngân sách/ngày kết thúc, chưa phải hosting hoạt động liên tục 24/7.

## 2. Docker nằm trên máy nào?

| Nơi | Vai trò | Có cần bật để dùng web? |
|---|---|---|
| **EC2 cloudbox-app-01** | Docker Engine chạy website, PostgreSQL và tunnel | **Có**; được thiết lập khởi động cùng máy |
| **Laptop Windows** | Docker Desktop phục vụ lập trình hoặc đóng gói bản cập nhật | **Không**; chỉ mở khi cần làm các việc đó |

Trên EC2, Docker chạy ba **container** (dịch vụ):

- **portal:** giao diện và API CloudBox.
- **db:** PostgreSQL, giữ tài khoản, gói, đơn hàng và thông tin tệp.
- **tunnel:** nối tên miền Cloudflare tới Portal.

**Image** là bản đóng gói ứng dụng; **volume** là nơi giữ dữ liệu; **Compose** là cấu hình các dịch vụ. Thay container Portal không có nghĩa xóa volume.

Luồng truy cập: **trình duyệt → Cloudflare → tunnel trên EC2 → CloudBox**. Laptop không nằm trong luồng này. Root `start-local.ps1/.cmd` chỉ là công cụ local, không bật hoặc triển khai website AWS.

## 3. Máy EC2 đã Running nhưng web chưa lên

Mở **AWS → EC2 → Instances**, kiểm tra đúng máy `cloudbox-app-01` tại vùng **us-east-1 (N. Virginia)**. Chờ máy hoàn tất kiểm tra trạng thái.

Nếu vẫn lỗi, SSH vào EC2 theo [hướng dẫn AWS](docs/operations/AWS-ACADEMY.md). **Chỉ chạy các lệnh Bash sau trên EC2**, không chạy trong PowerShell laptop:

```bash
cd /opt/cloudbox
sudo docker compose -f compose.aws.yml -f compose.tunnel.yml ps
```

Mong đợi: `portal` và `db` là `healthy`, `tunnel` là `Up`. Nếu các dịch vụ đang dừng, bật lại bằng:

```bash
sudo docker compose -f compose.aws.yml -f compose.tunnel.yml up -d --wait
curl -fsS http://127.0.0.1:8000/healthz
```

Kết quả kiểm tra ứng dụng cần là `{"status":"ok"}`. Nếu Docker chưa chạy, SSH bị timeout hoặc thiếu volume/config, xem bảng xử lý trong [hướng dẫn AWS](docs/operations/AWS-ACADEMY.md). Không cài lại database hoặc tạo kho trống để chữa lỗi.

## 4. Muốn đưa bản sửa lên web

**Chỉ làm khi sửa ứng dụng; không làm mỗi lần mở web hoặc chỉ sửa README.** Việc sửa mã trên laptop chưa thay đổi website AWS.

1. **Laptop:** sửa mã và kiểm thử bằng dữ liệu riêng.
2. **Laptop:** mở Docker Desktop, build image mới từ `apps/portal`, rồi xuất image thành tệp `.tar`.
3. **Laptop → EC2:** chuyển image bằng SCP, đối chiếu SHA-256.
4. **EC2:** nạp image, đặt tên image mà Compose đang dùng.
5. **EC2:** cập nhật **riêng portal**, giữ nguyên `db`, `tunnel`, cấu hình bí mật và volume.
6. **Website:** kiểm đăng nhập, mở kho, tải lên/tải xuống và phần vừa sửa.

Các lệnh PowerShell/Bash đầy đủ, theo đúng thứ tự: **[Triển khai và vận hành AWS](docs/operations/AWS-ACADEMY.md)**. Nếu bản mới thay schema/database, cần kế hoạch migration riêng trước khi triển khai.

## 5. Cấu hình và dữ liệu đang ở đâu?

| Thành phần | Vị trí hiện hành |
|---|---|
| Ứng dụng AWS | `/opt/cloudbox` trên EC2 |
| Compose trên AWS | `compose.aws.yml` và `compose.tunnel.yml` trong thư mục trên |
| Cấu hình ứng dụng, Gmail, thanh toán | `/opt/cloudbox/private/portal.env` trên EC2 |
| Cấu hình PostgreSQL | `/opt/cloudbox/private/db.env` trên EC2 |
| Tài khoản, đơn hàng, metadata | Database `portal`, volume `cloud-storage_db_data` trên EC2 |
| Nội dung tệp và phiên bản | Volume `cloud-storage_cloudbox_data` trên EC2 |
| Mã nguồn và dữ liệu nguồn lúc chuyển | Laptop; không tự đồng bộ hai chiều với AWS |

**Sửa `.env` trên laptop không cập nhật website AWS.** Muốn đổi Gmail/config production, người dùng chỉnh trực tiếp trên EC2 và nạp lại riêng Portal theo hướng dẫn. Không gửi mật khẩu/token vào chat, log hoặc Git; không chép đè config bằng tệp ví dụ.

Giữ nguyên dữ liệu nguồn. AWS đã nhận thay đổi mới nên không bật lại bản laptop rồi đổi DNS để quay về ngay. Không `down -v`, prune volume, `remove-orphans`, Reset lab hoặc tạo database/volume rỗng thay dữ liệu đang có. Chưa thiết lập sao lưu dài hạn.

## 6. Chức năng chính

- Đăng ký bằng Gmail thật, xác minh mã 6 số, đăng nhập và khôi phục mật khẩu trong cùng CloudBox.
- Tệp/thư mục, tải lên/tải xuống, chia sẻ, thùng rác, phiên bản và không gian nhóm theo gói.
- Gói dịch vụ, đơn hàng và xử lý thanh toán.

| Gói | Quota tài khoản | Giá tháng |
|---|---:|---:|
| Miễn phí | 5 GiB | 0đ |
| Cơ bản | 100 GiB | 39.000đ |
| Tiêu chuẩn | 500 GiB | 89.000đ |
| Cao cấp | 2048 GiB | 199.000đ |

Kỳ 12 tháng thanh toán 10 tháng. Các giá trị hiển thị GB/TB dùng hệ số 1024 như hiện tại. **Toàn hệ thống vẫn dùng chung pool thử nghiệm 20 GiB**; quota 2 TB không có nghĩa máy chủ có sẵn ổ 2 TB. Giá/quota thực tế do database quản lý.

## 7. Mã nguồn, kiểm thử và tài liệu

- `apps/portal/frontend`: React/TypeScript; entry `src/main.tsx`.
- `apps/portal/backend`: FastAPI; entry `app.main:app`.
- `packages/design-system`: token và font dùng chung.
- `infrastructure/aws`: bản source của Compose AWS, không chứa secrets.
- Root Compose và `start-local`: công cụ local, không phải lệnh production AWS.

[Phát triển/kiểm thử](docs/development/DEVELOPMENT.md) · [Vận hành AWS](docs/operations/AWS-ACADEMY.md) · [Cấu trúc dự án](docs/architecture/PROJECT-STRUCTURE.md) · [Thuật ngữ](GLOSSARY.md) · [Thiết kế kho tệp](docs/architecture/STORAGE-MODULE.md)

Chuyển AWS ngày 10/11/2026 đã đối chiếu dữ liệu và được người dùng xác nhận đăng nhập/tải lên/tải xuống thành công. Xem [báo cáo chuyển AWS](artifacts/qa/aws-deployment-2026-11-10.md). Lịch sử [dọn source](artifacts/qa/deadcode-cleanup-2026-11-10.md) và [chốt cấu trúc](artifacts/qa/structure-final-2026-11-10.md) được giữ trong báo cáo, không phải các bước phải chạy lại.

<details>
<summary>Chi tiết xác minh, kho tệp và quyền lợi gói — dành cho phát triển/bảo trì</summary>

Đăng ký mới chỉ nhận `@gmail.com`, không tự gộp dấu chấm hoặc dấu cộng. Tài khoản cũ tiếp tục đăng nhập, kể cả email khác Gmail; tài khoản đã xác minh không phải xác minh lại.

Mã gồm 6 số, một lần, hết hạn 10 phút, tối đa 5 lần nhập. Gửi lại chờ 60 giây, tối đa 5 lần/giờ mỗi email và có giới hạn theo nguồn yêu cầu. OTP lưu HMAC, không trả về API hoặc ghi log. Mã mới thay mã cũ. Đăng ký chưa xác minh chưa tạo tài khoản người dùng/kho dư. Quay lại đăng ký để nhập lại nếu nhầm email.

Gửi lại nằm trong màn xác minh. Thành công gửi SMTP chỉ có nghĩa máy chủ nhận yêu cầu gửi, không bảo đảm thư đã vào inbox. Kiểm tra cả spam khi chờ thư. Khôi phục mật khẩu dùng liên kết một lần trong 30 phút, cùng miền CloudBox.

## Tệp và hạn mức

- Tất cả thao tác tệp dùng phiên CloudBox; người dùng mở `/dashboard#storage`, quản trị mở `/files#storage`.
- Thư mục, tìm kiếm/sắp xếp, đổi tên/di chuyển, tải tệp/thư mục lên, tải tệp xuống, thông tin và các phiên bản đã chuyển.
- Tải lên chia thành khối 8 MiB, có tiến trình/hủy, kiểm tra offset và giữ chỗ dung lượng. Dọn phiên tải chưa hoàn tất khi hết hạn 24 giờ.
- Liên kết `/s/...` chỉ xem/tải xuống, có thể thu hồi. Không hỗ trợ cộng tác sửa trực tiếp qua liên kết trong phiên bản này. Người bị khóa không tiếp tục công khai tệp qua liên kết cũ.
- Thùng rác hỗ trợ khôi phục; trùng tên khi khôi phục báo lỗi để tránh ghi đè. Nếu thư mục cha đã mất, khôi phục về gốc.
- **Thùng rác và nội dung phiên bản được lưu vẫn tính vào dung lượng.** Xóa vĩnh viễn có xác nhận và xóa cả phiên bản liên quan. Dọn blob sau khi commit metadata, có hàng đợi thử lại nếu ổ đĩa tạm lỗi. Dữ liệu Nextcloud nguồn không bị thao tác này xóa.
- Quota lấy từ gói đang hoạt động trong DB; khóa theo người dùng trên PostgreSQL bảo vệ các yêu cầu đồng thời. Hạ gói dưới dung lượng đã dùng giữ tệp, chặn tải thêm cho đến khi đủ chỗ.

Cloudflare hiện giới hạn kích thước mỗi request theo gói; cơ chế khối 8 MiB tránh gửi nguyên tệp lớn trong một request. Xem [giới hạn Cloudflare](https://developers.cloudflare.com/support/troubleshooting/http-status-codes/4xx-client-error/error-413/). Việc tải tệp lớn qua public vẫn cần kiểm thử theo môi trường thực tế.

Giá và quota hiện hành lấy từ bảng `plans`, không từ ảnh cũ. Kỳ 12 tháng thanh toán 10 tháng. Giữ nguyên các giao dịch và hạn gói; callback có chữ ký và kích hoạt gói được commit cùng trạng thái đơn, tránh ghi nhận paid nhưng chưa cấp gói khi gián đoạn.

## Quyền lợi gói thử nghiệm — cập nhật 09/11/2026

Theo yêu cầu mới nhất của chủ dự án ngày 09/11/2026, khôi phục hạn mức cho cả tài khoản cũ: Miễn phí **5 GB**, Cơ bản **100 GB**, Tiêu chuẩn **500 GB**, Cao cấp **2 TB**. Đây là hạn mức mô phỏng; toàn hệ thống vẫn bị giới hạn tổng 20 GiB để bảo vệ ổ đĩa thật. Giữ giá tháng 0 / 39.000 / 89.000 / 199.000đ và kỳ 12 tháng thanh toán 10 tháng. Số GB hiển thị dùng hệ số 1024 như trước.

Compose đặt `STORAGE_POOL_LIMIT_BYTES=21474836480` (20 GiB cho toàn hệ thống). Ngân sách chung tính tệp, thùng rác, nội dung phiên bản và kích thước đang giữ chỗ. Đây không phải dung lượng riêng cho từng tài khoản. Hết ngân sách hoặc gần đầy filesystem sẽ chặn dữ liệu mới, không xóa dữ liệu cũ. Quản trị xem ngân sách ở Tổng quan quản trị.


| Gói | Quyền lợi bổ sung |
|---|---|
| Miễn phí | Quản lý tệp, chia sẻ/thu hồi liên kết, thùng rác, truy cập trình duyệt |
| Cơ bản | Cập nhật tệp có lưu phiên bản 30 ngày; liên kết có hạn dùng |
| Tiêu chuẩn | Phiên bản 90 ngày; mật khẩu liên kết; yêu cầu nhận tệp |
| Cao cấp | Phiên bản 180 ngày; nhóm tối đa 5 người tính cả chủ; thống kê chia sẻ |

Quyền lợi được kiểm tra tại API theo gói và hạn dùng thực tế, không chờ tác vụ bảo trì. Giá các kỳ được tạo từ hàm tính tiền backend và dùng lại ở thẻ gói/checkout.

### Thao tác

- Trong Kho lưu trữ, mở menu tệp → **Cập nhật nội dung** để thay thế có chủ đích. Bản hiện tại được lưu vào lịch sử. Không tự ghi đè khi tải trùng tên.
- **Thông tin/Phiên bản**: tải bản cũ hoặc khôi phục; khôi phục giữ bản hiện tại và bản được chọn, cần đủ dung lượng. Thời hạn chụp tại lúc lưu phiên bản, không tự kéo dài sau đổi gói. Hết hạn truy cập không tự xóa blob; vẫn tính quota. Lịch sử nhập từ Nextcloud không bị chính sách mới tự xóa hoặc khóa.
- **Chia sẻ**: đặt hạn dùng với Cơ bản trở lên, đặt mật khẩu với Tiêu chuẩn trở lên. Mật khẩu băm scrypt; nhập sai bị giới hạn; cả trang xem và download đều kiểm tra quyền. Phiên mở khóa tồn tại một giờ cho đúng liên kết.
- **Yêu cầu nhận tệp**: chọn thư mục, hạn 1–30 ngày, tối đa 2 GiB/tệp, 10 GiB/yêu cầu, 20 lượt khởi tạo/giờ và 200 lượt/yêu cầu. Đây là trần kỹ thuật; quota tài khoản và ngân sách chung vẫn ưu tiên. Người gửi không có API liệt kê/đọc dữ liệu kho. Tên trùng báo lỗi, không ghi đè. Chỉ xem được liên kết lúc tạo, hãy sao chép trước khi rời trang.
- **Không gian nhóm**: mỗi chủ gói Cao cấp có một kho nhóm riêng. Mời tài khoản CloudBox đã xác minh; người được mời phải chấp nhận. Vai trò chủ/được chỉnh sửa/chỉ xem. Tối đa 5 người bao gồm chủ và lời mời còn hiệu lực; lời mời hết hạn sau 7 ngày. Chủ xóa thành viên để chấm dứt quyền truy cập; tệp họ đã gửi được giữ trong nhóm. Không chuyển quyền sở hữu tự động. Thư mục nhóm bị ẩn khỏi các API kho cá nhân.
- Tổng 2 TB của chủ gói dùng chung cho kho cá nhân, kho nhóm, phiên bản và thùng rác; không tạo thêm 2 TB hay nhân theo thành viên. Thành viên chỉ dùng API nhóm, không vào kho cá nhân chủ gói.
- Thống kê là lượt mở trang và yêu cầu tải đã được chấp nhận trong thời gian chủ liên kết có quyền lợi Cao cấp; không phải số người riêng biệt hay xác nhận tải xong. Không lưu IP/danh tính người xem trong bảng thống kê.

### Hết hạn và hạ gói

Giữ tệp, lịch sử và nhóm; quá quota chặn tải thêm. Không tạo phiên bản mới khi hết quyền lợi; phiên bản cũ còn trong thời hạn vẫn tải được, lịch sử nhập cũ vẫn đọc được. Liên kết đã tạo giữ mật khẩu/hạn dùng, không tự bỏ lớp bảo vệ khi hạ gói. Yêu cầu nhận tệp ngừng nhận nếu chủ hết quyền lợi. Kho nhóm chuyển chỉ đọc; chủ vẫn quản lý/thu hồi quyền thành viên. Các phiên tải của thành viên đã bị thu hồi không thể hoàn tất, giữ chỗ sẽ được giải phóng khi phiên bị hủy hoặc hết hạn.

</details>

<details>
<summary>Công cụ chuyển Nextcloud — lịch sử/bảo trì, không dùng để mở web</summary>

## Công cụ chuyển dữ liệu Nextcloud — chỉ dành cho bảo trì

Công cụ: `python -m app.features.storage.migrate`. Chỉ dùng trong container có source volume mount **read-only** tại `/legacy`, volume CloudBox tại `/data/cloudbox` và kết nối đúng hai database cũ. Chạy `--dry-run` trước; dùng `--admin-owner ID` để ánh xạ tài khoản quản trị đã được chấp thuận.

Đợt chuyển chính đã hoàn tất ngày09/11/2026. Quy trình dừng ghi nguồn → kiểm kê/copy/checksum → đối chiếu tài khoản/gói/đơn → mở CloudBox là lịch sử chuyển đổi, không phải bước khởi động hiện hành. Source dịch vụ cũ đã xóa; không khởi động lại chúng. Chỉ dùng importer trong môi trường bảo trì được chuẩn bị riêng và có nguồn mount read-only; không chạy lại trên kho đang vận hành để thử.

Importer chặn đường dẫn không an toàn, symlink, thiếu tệp, kho không có chủ đã duyệt, thay đổi đích, nội dung mã hóa, external mount hoặc quyền chia sẻ chưa có phương án chuyển. Không tự bỏ qua chúng. Các metadata phiên bản nguồn được giữ riêng; không khẳng định metadata nào cũng còn nội dung nếu Nextcloud trước đó đã dọn blob.

`--verify` kiểm tra lại kích thước/SHA-256 của tệp và phiên bản đích. Startup từ chối phục vụ tài khoản cũ nếu chưa có manifest chuyển dữ liệu, tránh mở nhầm một kho rỗng. Không tự chạy lại importer sau khi người dùng bắt đầu chỉnh sửa kho mới.

</details>

<details>
<summary>Lỗi Docker Desktop trên Windows ngày 09/11 — lịch sử, không phải cách sửa máy chủ AWS</summary>

### Docker lỗi engine.sock

Ngày 09/11 gặp lỗi `initializing Secrets Engine` do socket Windows cũ không truy cập/đổi tên được. Đã dừng Docker đang khởi động lỗi và đổi tên riêng hai thư mục runtime chỉ chứa socket 0 byte (`docker-secrets-engine` và `Docker/run`) sang tên `.blocked-...`, tạo lại thư mục trống và mở Docker. Không reset, không sửa VHDX hay volume; số tài khoản/đơn/tệp giữ nguyên. Các thư mục bị kẹt không chứa bản sao dữ liệu người dùng. Không chạy reset/prune/đăng ký lại WSL để xử lý lỗi này.

</details>
