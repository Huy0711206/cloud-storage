> Đường dẫn đã tổ chức lại ngày01/11/2026. Hướng dẫn hiện hành: README.md tại root; kết quả JSON và ảnh nằm artifacts/. Nội dung mô tả thời điểm QA trước đây vẫn là bằng chứng lịch sử, không mở lại các cổng cũ.

# Chẩn đoán và bản vá — 01/11/2026

Tài liệu này thay thế nhận định ban đầu về ba vấn đề trong UNIFIED-QA/README/PROGRESS. Bằng chứng lịch sử vẫn giữ nguyên, không xóa hoặc đổi kết quả cũ thành pass.

## 1. Phiên bản 404: phép thử trước gọi sai endpoint cho bản hiện tại

Đã tạo đúng một tài khoản Nextcloud chẩn đoán tạm, thử hai tệp rapid/spaced (hai lần ghi liên tiếp hoặc cách 12 giây), khôi phục bản đầu bằng native DAV. Không dùng tệp/tài khoản thật. Bản hiện tại sau restore đúng byte FIRST; bản trước đó SECOND tải từ archive HTTP200. Đã đối chiếu hàng oc_files_versions theo đúng fileid QA và tệp .v trong home QA; không sửa DB/retention hoặc chạy scan.

Nextcloud đưa cả bản hiện tại vào PROPFIND versions. Restore chuyển/move archive được chọn thành tệp hiện tại và đặt mtime về revision đã chọn. Vì vậy archive .v nguồn không còn nhưng nội dung vẫn có ở tệp hiện tại; entry đó cần tải từ files DAV. Kiểm tra cũ lặp GET mọi href archive đã phân loại sai bản hiện tại thành bản lịch sử bị hỏng. Trước restore, archive GET bản hiện tại cũng404; sau restore bản SECOND trở thành archive tải200. Bài thử raw sai endpoint ngay sau restore có lúc500, sau đó404: ghi nhận là ứng xử endpoint không phù hợp, không tính thành lỗi trên luồng native đã kiểm tra.

Browser xác nhận native sidebar đánh dấu Phiên bản hiện tại và dùng /remote.php/dav/files/.../spaced.txt; bản lịch sử dùng /remote.php/dav/versions/.../1793467086. Mở current đọc đúng FIRST; tải bản lịch sử bằng menu native thu được SECOND. Renderer Text có thể autosave tệp QA khi mở; việc kiểm byte API trước mở editor được lưu riêng. Xem DIAGNOSTICS-VERSIONS.json và diagnostics/2026-11-01/source-findings.md.

Không vá backend/database. Đây là sửa kết luận kiểm thử, không phải khôi phục được mọi lịch sử tệp thật. Chưa thử external storage/federated shares/encryption.

## 2. Viewer: vá hai fallback Sidebar cũ

Đã xác nhận close chỉ kiểm Sidebar tồn tại rồi gọi setFullScreenMode không tồn tại. Trong khi mở current với sidebar hiện, phát hiện thêm Sidebar.open không tồn tại. Mã Viewer đã emit viewer:sidebar:open trước fallback; Files NC35 có consumer native qua store mới. Bản vá giữ sự kiện đó, chỉ gọi hai phương thức legacy nếu typeof là function; giữ xử lý thoát fullscreen, không tạo hàm rỗng hoặc nuốt lỗi toàn cục.

Công cụ scripts/patch-viewer.py kiểm hash bản upstream và backup, mặc định dry-run; --apply và --restore. Module mới có tên hash để tránh cache cũ; module/map/info.xml gốc không sửa. Chỉ loader trỏ sang module mới. 17 regression tests chạy phần thân hàm thật đã trích; JS syntax/PHP lint đạt. Bằng chứng source và README nằm nextcloud/patches/viewer-close/.

**Ảnh hưởng cần biết:** đây là bản vá địa phương, không phải release chính thức. Integrity của app Viewer báo đúng 1 INVALID_HASH loader và 1 EXTRA_FILE module mới. Không tắt kiểm tra chữ ký hoặc thay signature. Core integrity được kiểm riêng. Sau nâng cấp upstream không tự áp lại; script từ chối hash lạ. Có thể restore để trả Viewer về nguyên gốc nhưng lỗi tương thích cũ sẽ quay lại.

## 3. Mail: tái hiện bên ngoài mã Mailpit

Bundle app.js đang phục vụ chỉ có 1 script chính, SHA lưu trong served-bundle-evidence.json; không có MutationObserver, có ResizeObserver khác loại. Thư QA chỉ có HTML/text tĩnh và attachment, không script/ảnh ngoài. Settings rỗng và thư HTML thử trong lượt kiểm tra trực tiếp chưa có lỗi đó.

Đã tái hiện CHÍNH XÁC TypeError MutationObserver trên trang tối giản không có Mailpit, không script, chỉ một iframe srcdoc tĩnh với cùng sandbox native. DOM xác nhận document.scripts.length=0. Xem iframe-minimal.html, minimal-browser-errors.json và mail-minimal-proof.png. Điều này chứng minh lỗi có thể phát sinh từ lớp môi trường trình duyệt/injection độc lập với ứng dụng; chưa có stack để xác định chính xác module của trình duyệt tích hợp. Không gán cho Go/SMTP/database hoặc vá Mailpit để che lỗi môi trường.

Máy chủ chẩn đoán chỉ bind loopback8766, tạm thời; không sửa CSP hoặc iframe sandbox của Mailpit. Proxy không hỗ trợ WebSocket, lỗi WS trên proxy không dùng làm bằng chứng lỗi Mail. Kết thúc phải dừng proxy, dọn đúng account/thư QA và credential tạm. Không thay phiên bản/dependencies Mailpit.

## Cách kiểm tra lại Viewer / khôi phục

```powershell
python scripts/patch-viewer.py
node --test apps/nextcloud/patches/viewer-close/viewer-close.test.mjs
# Khôi phục đúng Viewer gốc nếu cần:
python scripts/patch-viewer.py --restore
```

Giữ các cổng 8000/8080/8025; không thay URL hoặc tạo tunnel. Chi tiết dọn QA và kiểm tra cuối sẽ ghi trong DIAGNOSTICS-FINAL.json.

## Chốt thực tế

Browser đã tải module hash mới; mở bản text hiện tại đọc đúng FIRST, ảnh 500×500 giải mã đúng, đóng Viewer về danh sách và sidebar native còn mở; không có lỗi mới trong khoảng thử sau vá. Tải menu native của bản lịch sử trả đúng SECOND. Đã dọn một account/home Nextcloud, một thư QA, tệp tải thử và credential; counts về baseline. Đã dừng loopback8766. Core integrity exit0; app Viewer đúng hai phát hiện chữ ký dự kiến, lưu viewer-integrity.txt. Bằng chứng ở DIAGNOSTICS-FINAL.json và diagnostics/2026-11-01/.
