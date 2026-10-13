# Đối chiếu và xuất dữ liệu

Quản trị viên nhập tệp JSON khách hàng tại trang Quản trị. Mỗi phần tử phải có đủ các trường `ma_khach_hang`, `ho_ten`, `dia_chi`, `tuyen_dien`, `so_seri_cong_to`, `chi_so_khoi_tao` và `muc_dich_su_dung`. Hệ thống thêm mới hoặc cập nhật theo mã khách hàng và từ chối mã hoặc số serial bị trùng. Tệp tối đa 10 MB và 10.000 khách hàng mỗi lần nhập.

Sau OCR, mã được viết hoa và bỏ ký tự phân cách để đối chiếu. Ví dụ `PN2.001`, `PN2-001` và `PN2001` có cùng khóa tra cứu. Khi khớp, hệ thống dùng lại mã chuẩn từ cơ sở dữ liệu. Hiện mọi kết quả đều phải được con người xác nhận trước khi ghi dữ liệu tháng hoặc đưa vào tệp xuất chính thức.

Nút tạo báo cáo nằm trong trang Quản trị. Một lần tạo sinh đồng thời một tệp JSON và một tệp Excel có đúng cùng bảy trường, theo đúng thứ tự của tệp khách hàng đầu vào: `ma_khach_hang`, `ho_ten`, `dia_chi`, `tuyen_dien`, `so_seri_cong_to`, `chi_so_khoi_tao` và `muc_dich_su_dung`. Chỉ số chính thức của tháng được ghi vào `chi_so_khoi_tao`, vì vậy tệp xuất có thể dùng làm dữ liệu đầu kỳ tiếp theo. Mỗi khách hàng có tối đa một bản ghi chính thức trong một tháng. Kết quả chưa đối chiếu được với khách hàng hoặc chưa xác nhận không được xuất. Các trường hồ sơ trong báo cáo lấy từ hồ sơ khách hàng hiện tại, không phải bản chụp lịch sử hóa đơn.

Excel giữ mã khách hàng và số serial dưới dạng văn bản, chỉ số dưới dạng số nguyên, cố định hàng tiêu đề và hỗ trợ lọc. Các ký tự đầu công thức (`=`, `+`, `-`, `@`) bị vô hiệu hóa để ngăn chèn công thức. Tệp xuất chỉ tải được khi có phiên quản trị và thao tác nhập/xuất đều được ghi vào nhật ký truy vết.

## Chọn kỳ và báo cáo hết hiệu lực

Trang Quản trị có báo cáo tháng/năm; Vận hành có báo cáo danh sách đã xác nhận theo luồng của trang. Chỉ chọn kỳ có dữ liệu chính thức; số confidence không thêm vào định dạng bảy trường đã yêu cầu. Nếu xác nhận/sửa/từ chối làm dữ liệu tháng đổi, tạo lại báo cáo để tải số liệu mới. Tệp đã tải trước đó không tự cập nhật; ở tab khác hoặc ngoài trình duyệt cần chủ động tạo lại.

Mẫu JSON tương thích nhập ở [examples/customers.json](../examples/customers.json); đây là dữ liệu giả. File Excel dùng tên cột đúng bảy khóa trên, không phải bảng chi tiết tính tiền điện/hóa đơn pháp lý.
