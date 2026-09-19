# Kiến trúc

Đây là mô hình triển khai đơn giản trên một máy chủ. Nginx định tuyến lưu lượng trình duyệt cùng nguồn đến Next.js và FastAPI. FastAPI giao tiếp với PostgreSQL và vùng lưu trữ cục bộ gắn volume. Một tiến trình xử lý riêng nhận tác vụ từ PostgreSQL. PostgreSQL chỉ khả dụng trong mạng Docker; Nginx là dịch vụ duy nhất công khai cổng.

Các dependency AI và việc nạp mô hình được cô lập trong tiến trình xử lý nhằm duy trì ranh giới rõ ràng giữa API và quy trình AI.
