# Quy trình AI

Quy trình gồm các mô-đun độc lập để đánh giá chất lượng, tiền xử lý thận trọng, phát hiện vùng hiển thị đồng hồ, OCR mã khách hàng, đọc chỉ số, kiểm tra hợp lệ và tính độ tin cậy. Ảnh gốc luôn được giữ nguyên.

Phiên bản khởi đầu sử dụng OpenCV, các mô hình ONNX dựng sẵn của RapidOCR và Tesseract làm phương án dự phòng. Hệ thống đọc nhãn như `ma kh KH004` và `mã kh PN2.001`, đồng thời chỉ nhận dạng dãy số nguyên trên hàng bánh số cơ học chính; bánh số thập phân màu đỏ và mọi phần sau dấu phẩy hoặc dấu chấm đều bị bỏ qua. Mã OCR được chuẩn hóa để đối chiếu không phụ thuộc dấu chấm/gạch, nhưng kết quả cuối dùng mã chuẩn trong bảng khách hàng. Kết quả chỉ tự động xác nhận khi có đủ mã khách hàng, số điện nguyên, khớp khách hàng và độ tin cậy lớn hơn `confidence_ok_threshold` (mặc định `0.9`); các kết quả khác chuyển sang kiểm duyệt thủ công. Bản ghi `ai_results` bất biến lưu dòng OCR, vùng phát hiện, thành phần độ tin cậy và phiên bản mô hình `meter-ocr-baseline-v2-integer`.

Độ tin cậy của mô hình cơ sở là điểm tổng hợp theo quy tắc, chưa phải xác suất đã được hiệu chuẩn trên tập dữ liệu thực tế. Cần theo dõi nhật ký tự động xác nhận và đánh giá lại ngưỡng khi có tập nhãn đủ lớn.

Mô hình cơ sở này dùng để thu thập nhãn đã xác minh trong giai đoạn dữ liệu thực tế còn hạn chế. Pipeline huấn luyện tích hợp tạo bộ phân loại bánh số từ các nhãn thủ công, đăng ký artifact theo phiên bản/checksum và chỉ đưa vào worker sau khi quản trị viên kích hoạt. Model được huấn luyện bổ trợ phần đọc chữ số; OCR mã khách hàng vẫn dùng OCR cảnh dựng sẵn.
