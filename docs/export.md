# Đối chiếu và xuất dữ liệu

Quản trị viên nhập tệp JSON khách hàng tại trang Quản trị. Mỗi phần tử phải có đủ các trường `ma_khach_hang`, `ho_ten`, `dia_chi`, `tuyen_dien`, `so_seri_cong_to`, `chi_so_khoi_tao` và `muc_dich_su_dung`. Hệ thống thêm mới hoặc cập nhật theo mã khách hàng và từ chối mã hoặc số serial bị trùng. Tệp tối đa 10 MB và 10.000 khách hàng mỗi lần nhập.

Sau OCR, mã được viết hoa và bỏ ký tự phân cách để đối chiếu. Ví dụ `PN2.001`, `PN2-001` và `PN2001` có cùng khóa tra cứu. Khi khớp, hệ thống dùng lại mã chuẩn từ cơ sở dữ liệu. Kết quả trên ngưỡng tin cậy chỉ được tự động xác nhận khi tìm thấy khách hàng; kết quả không khớp chuyển sang kiểm duyệt.

Nút tạo báo cáo nằm dưới danh sách “Đã xác nhận” trên trang Vận hành. Một lần tạo sinh đồng thời một tệp JSON và một tệp Excel với cùng dữ liệu: hồ sơ khách hàng theo tệp nguồn, `chi_so_moi`, `do_tin_cay` và `ket_qua_doi_chieu`. Bản ghi không tìm thấy khách hàng vẫn được xuất với thông tin hồ sơ để trống và trạng thái `KHONG_TIM_THAY`, nhờ đó không che giấu sai lệch.

Excel giữ mã khách hàng và số serial dưới dạng văn bản, chỉ số dưới dạng số nguyên, độ tin cậy dưới dạng phần trăm, cố định hàng tiêu đề và hỗ trợ lọc. Các ký tự đầu công thức (`=`, `+`, `-`, `@`) bị vô hiệu hóa để ngăn chèn công thức. Tệp xuất chỉ tải được khi có phiên quản trị và thao tác nhập/xuất đều được ghi vào nhật ký truy vết.
