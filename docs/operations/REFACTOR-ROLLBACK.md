> **Tài liệu lịch sử trước chuyển đổi native và xóa source ngày10/11/2026.** Các lệnh/đường dẫn ba dịch vụ bên dưới ghi nhận trạng thái cũ, không chạy trên dự án hiện hành. Xem [README](../../README.md) và [cây hiện hành](../architecture/PROJECT-STRUCTURE.md). Nội dung lịch sử được giữ nguyên bên dưới.

# Khôi phục cấu trúc trước refactor

Snapshot private: `.unified-backup/refactor-20261101/source.zip`; manifest SHA256 cùng thư mục. Đã xác nhận ZIP đọc được, lưu475tệp nguồn/cấu hình và git status/diff trước sửa. Snapshot chứa .env nên không chia sẻ/commit. Không chứa node_modules/dist/cache, .online, data volumes; đó không phải bản sao database.

## Chuẩn bị bản khôi phục để review

Từ root, giải nén ra thư mục riêng trong .runtime thay vì ghi đè dự án:

```powershell
python -m zipfile -t .unified-backup/refactor-20261101/source.zip
python -m zipfile -e .unified-backup/refactor-20261101/source.zip .runtime/refactor-review
```

Đối chiếu source-manifest.json và artifacts/qa/refactor-file-map.json. Trước khi áp dụng thật, snapshot thay đổi phát sinh sau refactor; tuyệt đối không dùng git reset/clean để gộp cả thay đổi của người dùng.

## Áp dụng có kiểm soát nếu cần

1. Dừng portal/nextcloud ngắn trong thời gian đổi source/mount; không down -v, không dừng/xóa volume database.
2. Chép lại các source directories cũ từ bản review theo map, đồng thời phục hồi Dockerfile/Compose/root scripts cũ tương ứng. Không trộn Compose cũ với mount nguồn mới.
3. Không chép đè .env, export CSV, .online hoặc .unified-backup đang dùng. Người dùng hiện chọn local; không khôi phục cấu hình public chỉ vì snapshot trước đó đang online.
4. Giữ nguyên database/mail/file volumes và app Viewer trong nextcloud_data. Nếu cần thay Viewer sử dụng rollback riêng có SHA guard, không chép snapshot data.
5. Build image portal rồi khởi động cùng Compose project root. Kiểm health, đúng3ports và dữ liệu trước khi coi khôi phục đạt.

Các thư mục mới có thể tạm giữ để đối chiếu, không tự xóa source/backup chưa được duyệt. Quy trình restore source toàn phần chưa chạy trên hệ thống thật ở cuối phiên; chỉ ZIP integrity, các dry-run UI rollback và strict Viewer patch được kiểm chứng. Không tuyên bố đã kiểm thử hồi phục database.
