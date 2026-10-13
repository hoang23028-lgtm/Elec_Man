# Kiểm tra giao diện ngày 12/10/2026

> Báo cáo lịch sử theo ngày, không phải hướng dẫn bản hiện hành. Xem [danh mục tài liệu](../README.md).

## Phạm vi và kết quả

Kiểm tra trực tiếp bản đang chạy tại localhost bằng trình duyệt. Người dùng tự đăng
nhập tài khoản quản trị toàn hệ thống. Không tải thêm ảnh, lưu nhãn, xác nhận,
từ chối, đổi tài khoản, sửa cấu hình hoặc kích hoạt mô hình trên dữ liệu thật.

- Trước đăng nhập: Tổng quan tải được, navbar chỉ có Tổng quan và đăng nhập/đăng ký;
  bộ lọc và thông báo chỉ xem hiện đúng. Hộp thoại đăng nhập đưa focus vào tên đăng nhập.
- Sau đăng nhập: hiển thị vai trò quản trị toàn hệ thống và đủ sáu mục điều hướng.
- Vận hành: 37 ảnh cần xử lý đều đã gắn nhãn, 24 ảnh từ chối, chưa có ảnh xác nhận.
  Chuyển sang trang 2 bắt đầu từ STT 13; chọn trực tiếp trang 4 hiển thị STT 37,
  đúng một ảnh. Nhãn chỉ số và vùng đã lưu được tải lại khi chọn ảnh.
- Quan sát bố cục ở viewport mặc định hẹp và desktop 1440×1000. Desktop có ảnh
  phóng tới vùng công tơ, vùng người dùng màu đỏ và vùng tự động màu xanh.
- Các lô dữ liệu: tải bảng 11 lô, có phân trang; mở được chi tiết lô 43 ảnh với
  phân trang riêng. Không chạy lại xử lý lô.
- Quản trị: tải danh sách khách hàng; mở được tab Chỉ số tháng với bộ lọc và
  trạng thái không có bản ghi đã xác nhận.
- Vòng đời mô hình: hiển thị 37 mẫu hợp lệ/ngưỡng 200; nút Huấn luyện ngay bị
  vô hiệu hóa. Cấu hình triển khai chỉ đọc được vô hiệu hóa và có giải thích.
- Truy vết: tải được bảng sự kiện, bộ lọc hành động và sự kiện đăng nhập vừa thực hiện.
- Không có lỗi/cảnh báo console được công cụ trình duyệt ghi nhận trong lượt kiểm tra.
- `npm --prefix frontend run lint` và `npm --prefix frontend run typecheck` đạt.

## Điểm cần theo dõi

1. Lịch sử huấn luyện hiển thị lần chạy ngày 01/10/2026 gồm 30 mẫu huấn luyện,
   7 mẫu kiểm định và 0% đọc đúng toàn chuỗi. Đây là số liệu hiển thị của lần chạy
   cũ, chưa phải đánh giá độc lập hiện tại. Cần xem metrics, trạng thái bộ đọc và
   cách chia dữ liệu trước khi kết luận nguyên nhân hoặc kích hoạt mô hình.
2. Nhãn tổng quan lô ghi “1 lô đang xử lý” trong khi lô còn hoạt động đang ở
   trạng thái tải lên, 0 ảnh. Nên phân biệt đang tải và đang xử lý; chưa sửa trong lượt này.
3. Cột tên ảnh trên desktop khá hẹp với tên file dài. Cần kiểm tra thêm chế độ
   tập trung ảnh và màn hình hẹp trước khi điều chỉnh bố cục.

## Giới hạn

Đây là kiểm tra khói giao diện với thao tác đọc/điều hướng, không phải E2E đầy đủ.
Chưa kiểm tra lưu nhãn, xác nhận và từ chối qua trình duyệt trên môi trường riêng;
các thao tác ghi này đã được kiểm tra ở tầng API bằng PostgreSQL tạm.
Chưa đăng nhập trực tiếp hai vai trò ADMIN/VIEWER trong lượt UI này; phân quyền
của chúng đã có kiểm thử tích hợp API. Chưa kiểm tra đầy đủ bàn phím, trình đọc
màn hình hoặc mọi breakpoint. Không coi số lượng mẫu đạt ngưỡng là bằng chứng
mô hình đủ chính xác để vận hành tự động.
