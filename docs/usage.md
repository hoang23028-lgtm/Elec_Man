# Hướng dẫn sử dụng

## 1. Đăng nhập và điều hướng

Mọi người vào **Tổng quan** khi mở website. Khách và VIEWER chỉ xem; ADMIN làm nghiệp vụ; SUPER_ADMIN quản lý thêm tài khoản, huấn luyện, cấu hình và truy vết. Quyền được kiểm tra tại server, không chỉ ẩn menu. Đăng ký không tự kích hoạt/cấp quyền.

## 2. Chuẩn bị danh sách khách hàng

Quản trị → Khách hàng → nhập JSON có bảy trường theo [mẫu giả](../examples/customers.json), hoặc thêm thủ công. Kiểm tra tổng số tạo/cập nhật và số đối chiếu. Mã chuẩn giữ định dạng database, ví dụ PN2.001; đối chiếu chuẩn hóa chỉ hỗ trợ tìm kiếm, không đổi mã xuất thành chuỗi mất ký tự.

Mục đích sử dụng lấy từ dữ liệu khách hàng. Hồ sơ có mục đích chưa ánh xạ biểu giá vẫn nhập được nhưng chưa tính được tiền; không ép mọi khách hàng về một loại. Import là cập nhật theo mã, không tự xóa khách hàng vắng trong tệp.

## 3. Tải và xử lý ảnh

Vận hành → tạo/chọn lô → chọn thư mục/ảnh → Tải lên và xử lý. Chỉ dùng JPEG/PNG/WebP hợp lệ. Mỗi ảnh có giới hạn; năm luồng upload không phải năm worker OCR. Giao diện hiển thị đã chọn, đã tải, lỗi và còn lại. Ảnh vào hàng đợi, không chờ nhận dạng trong request upload.

Các lô dữ liệu cho phép lọc, phân trang, xem danh sách ảnh/kết quả trong từng lô. STT tính theo trang; nút chọn trang không thay đổi dữ liệu.

## 4. Gắn nhãn trước khi xác nhận

Trong Vận hành chọn **Cần xử lý**; bộ lọc phụ phân biệt Chưa gắn nhãn/Đã gắn nhãn. Chọn ảnh, phóng to hoặc dùng chế độ tập trung.

1. Chọn Vùng công tơ, click bốn góc theo thứ tự quanh vùng; chỉnh kéo góc nếu cần rồi Lưu vùng công tơ.
2. Chọn Vùng chỉ số, khoanh chỉ các bánh số nguyên, bỏ bánh đỏ/phần thập phân.
3. Bấm Xác định chỉ số để OCR lại vùng; kết quả vẫn cần xử lý, không tự xác nhận.
4. Sửa chuỗi số đúng và Lưu nhãn chỉ số. Giữ số 0 ở đầu khi gắn nhãn. Không có mã khách hàng vẫn lưu nhãn được.
5. Làm mới/chọn lại ảnh để kiểm tra nhãn đã lưu. Không đóng trang khi còn bản nháp chưa lưu.

Vùng người dùng màu đỏ, vùng tự động màu xanh. Điểm/zoom chỉ là điều khiển giao diện; vị trí nhãn lưu theo ảnh gốc. Vùng toàn công tơ và vùng bộ số là hai nhãn khác nhau; lưu một vùng không tự tạo vùng còn lại.

## 5. Xác nhận dữ liệu tháng

Kiểm tra mã khách hàng đã khớp database, chỉ số nguyên và kỳ tháng/năm rồi xác nhận. Nhãn LABELED **không** là chỉ số chính thức. Confidence cao cũng không bỏ qua con người ở phiên bản hiện tại.

Mỗi khách hàng chỉ có một ảnh xác nhận mỗi tháng. Xung đột 409 cần đối chiếu ảnh cũ, không tải lại để ghi đè. Lỗi 412 nghĩa ảnh đã đổi từ phiên khác; nạp lại trước khi sửa.

Đã xác nhận vẫn chỉnh sửa được với nhật ký trước/sau. Từ chối ảnh đã xác nhận yêu cầu xác nhận lại ý định, có thể gỡ bản ghi tháng. Đã từ chối có thể khôi phục về Cần xử lý, nhãn hợp lệ được giữ. Xem [quy tắc kiểm duyệt](review.md).

## 6. Xem lịch sử, thống kê và xuất

Tổng quan lọc mã khách hàng/tháng/năm, hiển thị chỉ số và tiền **tạm tính**. Thiếu tháng liền trước hoặc biểu giá phù hợp được giải thích, không tự dùng số cũ nhiều tháng làm tiêu thụ một tháng.

Quản trị → Chỉ số tháng: lọc tháng/năm/mã để xem dữ liệu xác nhận, ảnh và lịch sử. Tạo báo cáo đúng kỳ rồi tải JSON/Excel. Chỉ dữ liệu đã xác nhận và đối chiếu được khách hàng mới xuất. Bảy trường báo cáo và ý nghĩa `chi_so_khoi_tao` xem [xuất dữ liệu](export.md).

## 7. Nhật ký và mô hình

SUPER_ADMIN xem Truy vết để đối chiếu ai làm gì, đối tượng, thời gian, trường trước/sau và lý do. OCR chạy nền không được trình bày là người dùng sửa tay. Không đưa mật khẩu/session token vào lý do hoặc ghi chú.

Vòng đời mô hình hiển thị mẫu đủ điều kiện, phiên train, metrics và mô hình. Học định vị, benchmark reader và fine-tune reader là các việc khác nhau; xem [hướng dẫn huấn luyện](training.md).

## 8. Cách hiểu trạng thái

| Trạng thái | Ý nghĩa | Có dữ liệu tháng chính thức? |
|---|---|---|
| PENDING / Chưa gắn nhãn | Chờ xử lý/kiểm tra, chưa có nhãn số hợp lệ | Không |
| LABELED / Đã gắn nhãn | Đã lưu nhãn để dùng/đánh giá, có thể chưa có mã hoặc tháng | Không |
| CONFIRMED / Đã xác nhận | Con người xác nhận mã, số, tháng | Có |
| REJECTED / Đã từ chối | Không dùng làm dữ liệu tháng | Không |

Trạng thái job OCR và trạng thái kiểm duyệt là hai khái niệm riêng. Job COMPLETED không đồng nghĩa ảnh CONFIRMED.
