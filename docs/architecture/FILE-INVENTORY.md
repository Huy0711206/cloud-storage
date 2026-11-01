# Danh mục tệp và quyết định dọn

Đối chiếu snapshot private trước sửa với đường dẫn hiện tại. [Ánh xạ JSON](../../artifacts/qa/refactor-file-map.json) / [CSV](../../artifacts/qa/refactor-file-map.csv) có từng tệp, vai trò, trạng thái, tham chiếu gợi ý và hash gốc. Không sửa baseline cũ để ép đạt. Tham chiếu là gợi ý văn bản có giới hạn; import động, tooling, fallback và rollback được khảo sát riêng.

Đã phân loại **475 tệp snapshot**; **0 tệp chưa xác định nơi giữ/chuyển**. Trạng thái: byte-identical: 402, moved/edited; see semantic/build checks: 59, compatibility wrapper + implementation: 8, split: 6.

| Nhóm | Bằng chứng | Quyết định |
|---|---|---|
| Backend/frontend hiện hành | Entrypoint, imports, manifest, route contracts, tests | Phân nhóm feature, giữ logic/URL |
| Renderer từng gọi preview | PortalApp vẫn dùng overview/landing renderer | Promote vào features; giữ CSS/JSX |
| Gateway Files/Mail cũ và PreviewApp | Không có service Compose; vẫn có build/test/fixture | Giữ legacy coherent, không chạy cổng cũ |
| Mailpit upstream | Build context/Dockerfile và hash toàn source | Chỉ chuyển nguyên thư mục, không chia lại vendor |
| Nextcloud theme/Viewer patch backup+fixture | Compose mount, manifest, strict SHA/rollback,17tests | Giữ hoạt động và cả bản gốc để khôi phục |
| Tài liệu cũ | Nội dung vẫn nói cổng trước hợp nhất hoặc kế hoạch thời điểm cũ | Lưu docs/history, không dùng khởi động |
| Báo cáo/console/ảnh | Bằng chứng QA có thời điểm; giá trị cũ không phải runtime config | Gom artifacts, giữ nội dung gốc |
| Font/generated CSS copies | Từ packages/design-system, Docker context cần bản cục bộ | Trùng lặp có chủ ý; sync-design là nguồn sinh |
| Root/script wrappers | Giữ command cũ và ROOT anchor | Trùng tên có chủ ý, không phải duplicate implementation |
| cloudbox-don-hang.csv | Export nghiệp vụ, không phải source/test | Giữ nguyên, không xóa hoặc đưa vào artifacts |

## Ứng viên có thể dọn sau, chưa xóa

- Legacy gateways/preview: chỉ cân nhắc bỏ khi quyết định không cần tham chiếu/build/test/rollback; phải hỏi người dùng về danh sách cụ thể.
- CSS cloudbox-<hash> cũ không được manifest hiện tại chọn: có thể còn cache/rollback; giữ, không nhầm thành runtime active.
- UI atoms không có import hiện tại: thuộc registry component có thể tái sử dụng; chưa đủ căn cứ xóa chỉ vì tìm kiếm không thấy.
- node_modules/dist/pycache là output/cache, được ignore; không đưa vào source snapshot và không biến thành source archive. Không tự xóa trong đợt này.
- Nhóm trùng byte nằm trong [duplicate report](../../artifacts/qa/refactor-duplicate-groups.json); gồm font deploy, patch original/fixture, init và bằng chứng. Trùng byte không đồng nghĩa dư thừa.

Không xóa vĩnh viễn source, tài liệu hoặc backup nghi ngờ trong đợt tái cấu trúc. Các module monolithic được thay bằng định nghĩa đã di chuyển, không bỏ nghiệp vụ. Các tệp bọc gọi command cũ là tương thích có chủ ý. Git untracked trước sửa đã snapshot và được giữ/ánh xạ, không coi là rác.
