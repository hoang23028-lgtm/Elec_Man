# Phân quyền tài khoản

| Chức năng | Người xem (VIEWER) | Quản trị vận hành (ADMIN) | Quản trị toàn hệ thống (SUPER_ADMIN) |
|---|---|---|---|
| Dashboard, lọc thống kê | Có | Có | Có |
| Tải ảnh, xử lý OCR, lưu nhãn, xác nhận/từ chối | Không | Có | Có |
| Các lô dữ liệu, khách hàng, chỉ số tháng, xuất báo cáo | Không | Có | Có |
| Tài khoản, cấp quyền, khóa/xóa tài khoản | Không | Không | Có |
| Huấn luyện, đánh giá, kích hoạt mô hình, cấu hình | Không | Không | Có |
| Nhật ký toàn hệ thống | Không | Không | Có |

Khách chưa đăng nhập vẫn chỉ xem dashboard công khai như trước. Lưu nhãn trong nghiệp vụ không đồng nghĩa được khởi chạy huấn luyện.

Backend kiểm tra quyền cho từng nhóm API; ẩn menu trên frontend chỉ hỗ trợ trải nghiệm, không thay thế kiểm tra quyền. Vai trò không hợp lệ bị từ chối. Đăng ký công khai luôn tạo tài khoản người xem chưa kích hoạt. Tài khoản mới do quản trị tạo mặc định là người xem.

Để cấp quyền: đăng nhập quản trị toàn hệ thống → Quản trị → Tài khoản → thêm/sửa tài khoản → chọn vai trò. Đổi vai trò thu hồi các phiên của tài khoản đó; người dùng cần đăng nhập lại. Thay đổi ghi log giá trị trước/sau. Không được tự hạ quyền, tự khóa/xóa hoặc loại bỏ quản trị toàn hệ thống cuối cùng.

Migration `20261005_0027` chuyển tất cả tài khoản ADMIN cũ thành SUPER_ADMIN để giữ nguyên quyền hệ thống đã có, không đổi mật khẩu hoặc dữ liệu nghiệp vụ. Sau nâng cấp, quản trị toàn hệ thống nên rà soát và chuyển các tài khoản chỉ làm nghiệp vụ về ADMIN. Script khởi tạo tài khoản đầu tiên tạo SUPER_ADMIN; không tự nâng quyền tài khoản đăng ký.

Downgrade về schema cũ gộp SUPER_ADMIN về ADMIN và làm mất phân tách quyền; không dùng để hạ quyền bảo mật.
