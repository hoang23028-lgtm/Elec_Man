# Đối chiếu và xuất dữ liệu

Quản trị viên nhập tệp JSON khách hàng tại trang Quản trị. Mỗi phần tử phải có đủ các trường `ma_khach_hang`, `ho_ten`, `dia_chi`, `tuyen_dien`, `so_seri_cong_to`, `chi_so_khoi_tao` và `muc_dich_su_dung`. Hệ thống thêm mới hoặc cập nhật theo mã khách hàng và từ chối mã hoặc số serial bị trùng. Tệp tối đa 10 MB và 10.000 khách hàng mỗi lần nhập.

Sau OCR, mã được viết hoa và bỏ ký tự phân cách để đối chiếu. Ví dụ `PN2.001`, `PN2-001` và `PN2001` có cùng khóa tra cứu. Khi khớp, hệ thống dùng lại mã chuẩn từ cơ sở dữ liệu. Kết quả trên ngưỡng tin cậy chỉ được tự động xác nhận khi tìm thấy khách hàng; kết quả không khớp chuyển sang kiểm duyệt.

Nút tạo báo cáo nằm trong trang Quản trị. Một lần tạo sinh đồng thời một tệp JSON và một tệp Excel có đúng cùng bảy trường, theo đúng thứ tự của tệp khách hàng đầu vào: `ma_khach_hang`, `ho_ten`, `dia_chi`, `tuyen_dien`, `so_seri_cong_to`, `chi_so_khoi_tao` và `muc_dich_su_dung`. Chỉ số đã xác nhận mới nhất trong tháng được ghi vào `chi_so_khoi_tao`, vì vậy tệp xuất có thể dùng làm dữ liệu đầu kỳ tiếp theo. Bản ghi không tìm thấy hồ sơ khách hàng vẫn giữ đúng bảy trường, với các thông tin hồ sơ chưa có để trống.

Excel giữ mã khách hàng và số serial dưới dạng văn bản, chỉ số dưới dạng số nguyên, cố định hàng tiêu đề và hỗ trợ lọc. Các ký tự đầu công thức (`=`, `+`, `-`, `@`) bị vô hiệu hóa để ngăn chèn công thức. Tệp xuất chỉ tải được khi có phiên quản trị và thao tác nhập/xuất đều được ghi vào nhật ký truy vết.
