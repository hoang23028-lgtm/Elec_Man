# Quy trình kiểm duyệt

Đầu ra AI là bất biến trong `ai_results`. Người kiểm duyệt chỉ ghi giá trị cuối cùng vào `meter_readings`; mỗi trường bị thay đổi tạo một bản ghi `manual_corrections` và mọi thao tác xác nhận/từ chối đều được kiểm toán. Giá trị đã sửa không bao giờ ghi đè giá trị AI.
