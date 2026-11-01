# Tiến độ CloudBox

## Quyết định hiện hành

- Ba cổng:8000 CloudBox,8080 Nextcloud native,8025 Mailpit native local. Không mở lại preview.
- Giữ dữ liệu/volume/tài khoản/quota/thư; portal và Nextcloud vẫn phiên riêng, không thêm SSO.
- Giữ Quick Tunnel hiện hành, .online/.unified-backup ở root/private.
- Viewer có bản vá hai fallback legacy; app signature cảnh báo dự kiến, không tắt integrity. Phiên bản404 là kết luận kiểm thử đã hiệu chỉnh. Mail observer thuộc môi trường iframe/injection chưa xác định module.

## Tái cấu trúc — 01/11/2026

Đã khảo sát trước, trình bày phương án và tạo source snapshot bảo vệ cả thay đổi chưa commit. Đã triển khai cấu trúc apps/packages/infrastructure/scripts/docs/artifacts, giữ root commands và Compose identity. Xem [kế hoạch](docs/architecture/REFACTOR-PLAN.md). Kết quả cuối ở artifacts/qa/refactor-verification.json khi có.

## Lịch sử đầy đủ

[PROGRESS trước tái cấu trúc](docs/history/PROGRESS-before-refactor.md) giữ toàn văn các giai đoạn cũ. Khi mâu thuẫn dùng quyết định hiện hành ở trên và [chẩn đoán mới](docs/qa/DIAGNOSTICS-2026-11-01.md).

## Chốt bàn giao

Đã ánh xạ475tệp, phân nhóm frontend/backend theo feature, giữ vendor/native/legacy coherent và root commands.76Python+10mailclient+17Viewer tests đạt; frontend/nativeMailDocker builds đạt. Production backend hash khớp source đã review;5dịch vụ khỏe, chỉ3cổng chính,17UIassets/fonts local tải200. Giữ các volume/tài khoản và .env/CSV. Người dùng chọn tunnel tắt, đã khôi phục local; không báo HTTPS đã kiểm khi offline. Khắc phục hằng IPV4 bị thiếu trong đợt tách và stale online override bằng kiểm thử. Không xóa source/backup/tài liệu nghi ngờ; xem docs/architecture/FILE-INVENTORY.md. Source rollback snapshot private và full history được giữ. Chi tiết kết quả/giới hạn ở artifacts/qa/refactor-verification.json.
