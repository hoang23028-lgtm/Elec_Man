# Quy trình kiểm duyệt

Đầu ra AI là bất biến trong `ai_results`. Trang Vận hành chia kết quả thành hàng chờ kiểm duyệt bên trái và dữ liệu đã xác nhận bên phải. Kết quả đầy đủ có độ tin cậy lớn hơn 90% (hoặc ngưỡng quản trị đang cấu hình) đi thẳng sang danh sách đã xác nhận và tạo sự kiện `AUTO_CONFIRM_RESULT`.

Người kiểm duyệt ghi giá trị cuối cùng vào `meter_readings`; mỗi trường bị thay đổi tạo một bản ghi `manual_corrections`. Mọi thao tác xác nhận, từ chối và sửa dữ liệu đã xác nhận đều được kiểm toán. Giá trị đã sửa không bao giờ ghi đè giá trị AI.
