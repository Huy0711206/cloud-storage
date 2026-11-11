# Vận hành CloudBox hiện hành

Production từ 10/11/2026 nằm trên EC2 AWS Academy `cloudbox-app-01`, không còn phục vụ từ Docker Desktop laptop. Tên miền duy nhất vẫn là https://cloudbox.rachiba.top.

- [Mở web hằng ngày và phân biệt Docker laptop/EC2](../../README.md).
- [AWS Academy: SSH, xử lý lỗi, triển khai từng bước và private config](AWS-ACADEMY.md).
- [Báo cáo chuyển dữ liệu và kiểm chứng](../../artifacts/qa/aws-deployment-2026-11-10.md).
- [Phát triển và kiểm thử local bằng dữ liệu riêng](../development/DEVELOPMENT.md).

Trên EC2, thư mục `/opt/cloudbox` có `compose.aws.yml` và `compose.tunnel.yml`; chạy cả hai để quản lý db/portal/tunnel. Source tương ứng ở `infrastructure/aws/`; cấu hình bí mật chỉ có trên EC2 trong `private/`.

Portal laptop đã dừng. Root start-local.ps1/.cmd và Compose Windows là công cụ local, không triển khai AWS. Không khởi động lại trên dữ liệu nguồn để tạo thêm production. Sau khi AWS nhận ghi mới, quay lại laptop đòi hỏi chuyển dữ liệu hiện tại từ AWS và kiểm chứng trước đổi DNS.

Giữ nguyên .env/.online/.runtime/.unified-backup/CSV, database/volumes và dữ liệu Nextcloud nguồn. Không down -v, remove-orphans, prune volume, Reset lab hoặc tạo volume rỗng thay dữ liệu hiện có. Không đổi mật khẩu DB chỉ bằng sửa env; không gửi toàn bộ config/log cho người khác.

AWS Academy có phiên lab/ngân sách/ngày kết thúc; không bảo đảm hosting 24/7 dài hạn. Không cài cơ chế tự gia hạn lab hoặc thay tự khởi động Windows. Chưa thiết lập backup dài hạn.
