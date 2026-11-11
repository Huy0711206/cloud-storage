# Lưu trữ CloudBox

Ngôn ngữ chung cho quyền truy cập kho và tiếp nhận tệp. Phân biệt người thực hiện thao tác với chủ kho và tài khoản chịu dung lượng giúp diễn đạt đúng việc dùng chung kho nhóm.

## Language

**Người thao tác (actor)**:
Người đang thực hiện một thao tác với kho, gồm chủ kho, thành viên nhóm hoặc người gửi qua yêu cầu nhận tệp. Người thao tác không nhất thiết là chủ kho hay người chịu dung lượng.
_Avoid_: Chủ kho, người chịu dung lượng (khi chỉ người thực hiện)

**Chủ kho**:
Tài khoản sở hữu kho cá nhân hoặc kho nhóm và có quyền quản lý kho đó. Thành viên tải tệp vào kho nhóm không trở thành chủ kho.
_Avoid_: Người tải lên, thành viên (khi chỉ chủ kho)

**Người chịu dung lượng**:
Tài khoản có hạn mức gói được dùng để tính tệp, phiên bản, thùng rác và giữ chỗ của kho. Với kho nhóm, đây là chủ kho nhóm; kho cá nhân và kho nhóm của chủ cùng dùng một hạn mức.
_Avoid_: Người thao tác, người gửi, hạn mức riêng của thành viên

**Kho cá nhân**:
Không gian tệp riêng của một tài khoản, gồm cả tệp nhận qua yêu cầu nhận tệp. Kho cá nhân không bao gồm kho nhóm của tài khoản đó.
_Avoid_: Toàn bộ tệp của chủ kho (khi chỉ kho cá nhân)

**Kho nhóm**:
Không gian tệp dùng chung do một chủ kho quản lý, với quyền truy cập riêng cho từng thành viên. Quyền vào kho nhóm không cấp quyền vào kho cá nhân của chủ.
_Avoid_: Kho cá nhân dùng chung, dung lượng riêng của nhóm

**Phiên tải**:
Một lần gửi tệp có tên, nơi nhận và kích thước dự kiến đã xác định, từ lúc bắt đầu đến khi hoàn tất, hủy hoặc hết hạn. Phiên tải thuộc kho cá nhân, kho nhóm hoặc một yêu cầu nhận tệp cụ thể.
_Avoid_: Tệp đã lưu, liên kết chia sẻ

**Yêu cầu nhận tệp**:
Lời mời gửi tệp vào một thư mục cá nhân đã chọn, có hạn dùng và giới hạn tiếp nhận. Người gửi chỉ được gửi tệp, không được xem hay tải dữ liệu trong kho nhận.
_Avoid_: Liên kết chia sẻ, thư mục công khai

**Giữ chỗ**:
Phần dung lượng dành cho một phiên tải đang chờ hoàn tất và còn hiệu lực, được tính vào hạn mức của người chịu dung lượng và ngân sách chung. Khi phiên tải hoàn tất, phần này trở thành dung lượng tệp đã lưu; khi hủy hoặc hết hạn, phần giữ chỗ được giải phóng.
_Avoid_: Dung lượng đã lưu, dung lượng miễn phí
