# Kiến trúc

Đây là mô hình triển khai đơn giản trên một máy chủ. Nginx định tuyến lưu lượng trình duyệt cùng nguồn đến Next.js và FastAPI. FastAPI giao tiếp với PostgreSQL và vùng lưu trữ cục bộ gắn volume. Một tiến trình xử lý riêng nhận tác vụ từ PostgreSQL. PostgreSQL chỉ khả dụng trong mạng Docker; Nginx là dịch vụ duy nhất công khai cổng.

Các dependency AI nặng được tách khỏi API và worker. Hai container nội bộ `reader-ppocr` và `reader-parseq` giữ model trong bộ nhớ, nhận vùng chỉ số đã hiệu chỉnh và trả dự đoán độc lập. Worker gọi hai dịch vụ song song rồi chỉ chấp nhận chuỗi khi chúng đồng thuận. Container `trainer` đọc ảnh, ghi artifact định vị vào volume model và cập nhật trạng thái phiên huấn luyện trong PostgreSQL. Worker chỉ đọc volume model và xác minh checksum trước khi nạp artifact đang hoạt động.
