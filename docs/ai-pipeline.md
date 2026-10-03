# Quy trình AI

Pipeline vận hành gồm bốn tầng: tiền xử lý ảnh, định vị mặt công tơ, định vị/hiệu chỉnh bốn góc vùng chỉ số và đọc toàn chuỗi. Ảnh gốc luôn được giữ nguyên.

Worker dùng OpenCV và các model định vị đã kích hoạt để cắt vùng chỉ số. Vùng này được gửi trong mạng Docker nội bộ tới dịch vụ `reader`; dịch vụ chạy PP-OCRv6 small và PARSeq-tiny trên CPU. Chỉ khi hai model trả về cùng chuỗi số hợp lệ thì hệ thống mới trả một đề xuất. Nếu một model từ chối, hai kết quả khác nhau, dịch vụ lỗi hoặc thiếu số bánh xe nguyên, ảnh được chuyển sang Human Review.

Mã khách hàng vẫn được RapidOCR đọc từ ảnh cảnh và đối chiếu với mã chuẩn trong PostgreSQL. Số điện chỉ lấy bánh số nguyên; bánh đỏ cuối cùng và phần sau dấu phẩy không được lưu.

Độ tin cậy của hai model là điểm chưa hiệu chuẩn. Vì tập test hiện còn nhỏ, điểm đồng thuận bị giới hạn dưới ngưỡng tự xác nhận 90%; người dùng phải xác nhận trước khi ảnh, chỉ số tháng và vùng khoanh được lưu chính thức. Sau khi có tập test độc lập đủ lớn, ngưỡng có thể được hiệu chỉnh bằng số liệu exact-match, coverage và precision khi tự xác nhận.

Dịch vụ đọc chuỗi không mở cổng ra host, không truy cập database, không truy cập volume ảnh và chạy với filesystem chỉ đọc. Trọng số được tải và đóng gói lúc build image; khi vận hành, mạng dữ liệu là mạng `internal` không có Internet.
