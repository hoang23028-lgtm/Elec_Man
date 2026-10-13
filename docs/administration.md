# Quản trị và truy vết

## Phân tách nghiệp vụ

ADMIN quản lý khách hàng, chỉ số tháng và báo cáo tại Quản trị. SUPER_ADMIN có thêm quản lý tài khoản; Vòng đời mô hình chứa huấn luyện, model registry và cấu hình hệ thống. Nhật ký toàn hệ thống tại Truy vết chỉ dành cho SUPER_ADMIN. Xem [ma trận quyền](roles.md).

## Khách hàng và dữ liệu tháng

Nhập JSON/thêm thủ công; xem hồ sơ, mục đích sử dụng và đối chiếu mã chuẩn. Import cập nhật theo mã không xóa người vắng trong file. Chỉ số tháng/ảnh chính thức chỉ được tạo sau xác nhận; bộ lọc tháng/năm/mã không biến nhãn thành dữ liệu chính thức.

Báo cáo chọn đúng kỳ, xuất JSON/Excel theo bảy trường khách hàng. Đầu vào tính tiền cũ được snapshot khi xác nhận; báo cáo hồ sơ lấy dữ liệu khách hàng hiện tại. Xem [lưu trữ](storage.md) và [xuất](export.md).

## Tài khoản

SUPER_ADMIN thêm, sửa tên/vai trò/trạng thái, đổi mật khẩu và xóa mềm. Vai trò mặc định VIEWER. Đăng ký công khai là VIEWER chưa kích hoạt; chỉ quản trị toàn hệ thống hiện hữu quyết định kích hoạt/cấp quyền.

Khóa/xóa/đổi vai trò thu hồi phiên liên quan. Không tự hạ quyền, tự khóa/xóa hay bỏ SUPER_ADMIN hoạt động cuối cùng. Xóa mềm giữ quan hệ nghiệp vụ và audit. Đổi mật khẩu chính mình giữ phiên hiện tại, thu hồi các phiên khác theo luồng API.

Bộ cài chỉ tạo quản trị đầu tiên, không dùng để reset mật khẩu hoặc nâng quyền tài khoản đã đăng ký.

## Cấu hình và mô hình

Chính sách động được validate/lưu database và ghi audit. Giới hạn upload/retry/poll trong UI chỉ đọc; đổi env và tạo lại đúng container mới có hiệu lực. Không tự restart dịch vụ ngầm.

Registry chỉ đọc file bên dưới MODELS_ROOT, xác minh checksum, bắt đầu TESTING. Kích hoạt loại model được hỗ trợ cần tối thiểu 30 ảnh validation tách theo nhóm đã xác minh và điểm vùng ≥0,8. Cùng loại chỉ một model active; thay đổi có khóa điều phối/audit. Không tải mã thực thi tùy ý từ frontend.

## Nhật ký hành động

Truy vết cho biết hành động tiếng Việt, actor người dùng/tiến trình, thời gian, đối tượng, ID, IP và chi tiết. Sửa mã khách hàng/chỉ số hiển thị trước → sau, trường đổi, lý do, trạng thái, ảnh/lô và AI gốc. Audit không ghi mật khẩu, session token hay CSRF.

Một thao tác kiểm duyệt bị xung đột không được giả là đã thành công. Revision ngăn phiên cũ ghi đè; transaction/cleanup giữ database và bản sao ảnh nhất quán trong các lỗi đã kiểm thử. Xem [quy trình kiểm duyệt](review.md).

Metrics vận hành trên ảnh được xác nhận không thay thế test độc lập và có thiên lệch chọn mẫu. `confidence_ok_threshold` là cấu hình theo dõi; tự xác nhận vẫn bị khóa trong code.
