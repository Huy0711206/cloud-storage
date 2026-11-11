# Lệnh CloudBox hiện hành

Root start-local.ps1/.cmd (implementation: development/start-local.ps1) chỉ phục vụ local; không triển khai AWS. Production đã chuyển sang EC2 ngày 10/11/2026, Portal laptop đã dừng. Không chạy lại trên dữ liệu nguồn để tạo production thứ hai. Xem [vận hành AWS](../docs/operations/AWS-ACADEMY.md).

- maintenance/sync-design.py: token/font CloudBox từ packages/design-system; scripts/sync-design.py giữ entry tương thích.
- operations/one-off/restore-plan-quotas.py: tác vụ ghi DB một lần, không chạy khi QA/khởi động thường ngày.
- Kiểm chứng: pytest backend, PostgreSQL cloudbox_qa riêng; pnpm check/build frontend; Compose health.

Quick Tunnel, Viewer/rollback/verifier cũ và wrapper của chúng đã xóa theo xác nhận10/11/2026. .online/.runtime/.unified-backup không di chuyển hoặc xóa. Xem ../artifacts/qa/deadcode-cleanup-2026-11-10.md.
