# Quy trình AI

Quy trình gồm các mô-đun độc lập để đánh giá chất lượng, tiền xử lý thận trọng, phát hiện vùng hiển thị đồng hồ, OCR mã khách hàng, đọc chỉ số, kiểm tra hợp lệ và tính độ tin cậy. Ảnh gốc luôn được giữ nguyên.

Phiên bản khởi đầu sử dụng OpenCV, các mô hình ONNX dựng sẵn của RapidOCR và Tesseract làm phương án dự phòng. Hệ thống đọc nhãn khách hàng như `ma kh KH004`, tìm hàng chữ số cơ học chính và thử nhận dạng riêng bánh số thập phân màu đỏ. Kết quả chỉ tự động xác nhận khi có đủ mã khách hàng, số điện và độ tin cậy lớn hơn `confidence_ok_threshold` (mặc định `0.9`); các kết quả khác chuyển sang kiểm duyệt thủ công. Bản ghi `ai_results` bất biến lưu dòng OCR, vùng phát hiện, thành phần độ tin cậy và phiên bản mô hình `meter-ocr-baseline-v1`.

Độ tin cậy của mô hình cơ sở là điểm tổng hợp theo quy tắc, chưa phải xác suất đã được hiệu chuẩn trên tập dữ liệu thực tế. Cần theo dõi nhật ký tự động xác nhận và đánh giá lại ngưỡng khi có tập nhãn đủ lớn.

Mô hình cơ sở này dùng để thu thập nhãn đã xác minh trong giai đoạn dữ liệu thực tế còn hạn chế. Đây không phải mô hình đồng hồ điện sản xuất đã được huấn luyện. Gói mô hình được huấn luyện và đánh giá trong tương lai phải triển khai cùng giao diện mô-đun và khai báo phiên bản mới trước khi kích hoạt.
