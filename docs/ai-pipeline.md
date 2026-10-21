# Quy trình AI vận hành

## Các tầng thực sự đang chạy

| Tầng | Cách làm hiện tại | Đầu ra |
|---|---|---|
| Tiền xử lý | OpenCV, chuẩn hóa/crop/hiệu chỉnh phối cảnh | Ảnh đầu vào reader; ảnh gốc không đổi |
| Định vị công tơ | Ridge hoặc MobileNetV3 ONNX đã vượt gate/được kích hoạt; phương pháp cơ sở khi chưa có | Bốn góc mặt công tơ |
| Định vị vùng chỉ số | Cặp Ridge/MobileNetV3 cùng phiên/kiến trúc, học trong mặt công tơ chỉnh phối cảnh; khi chưa có model dùng heuristic/OCR cảnh | Bốn góc vùng số nguyên |
| Đọc chỉ số | Hai dịch vụ riêng PP-OCRv6 small/PARSeq-tiny; PARSeq dùng safetensors đã fine-tune nếu được kích hoạt | Đề xuất toàn chuỗi số theo đồng thuận |

Không có mô hình học sâu tiền xử lý đã fine-tune riêng. Không gọi cả bốn tầng là bốn deep model đã huấn luyện. Chưa có model định vị đã kích hoạt thì vẫn có thể khoanh vùng thủ công để dùng hệ thống.

Mã khách hàng dùng RapidOCR trên ảnh cảnh và Tesseract fallback có ngân sách thời gian, sau đó đối chiếu mã chuẩn trong PostgreSQL. Tesseract không còn là bộ đọc chỉ số điện. Không có HOG từng ô trong luồng đọc chỉ số hiện tại.

## Đồng thuận và từ chối

Worker gửi crop phối cảnh tới hai reader nội bộ. Reader phải trả chuỗi nguyên hợp lệ với số bánh nguyên dự kiến. Khi xung đột, timeout, từ chối hoặc thiếu chữ số, hệ thống không đoán thêm kết quả; chuyển con người kiểm tra.

Đồng thuận hai reader **không bảo đảm đúng** khi crop sai. Score chưa hiệu chuẩn không phải xác suất đúng. Tự động xác nhận bị khóa trong code; tăng ngưỡng/giảm ngưỡng UI không tự mở lại. Mọi chỉ số chính thức cần xác nhận thủ công.

Bánh đỏ cuối, phần sau dấu phẩy không được tính vào chỉ số nguyên. Khi bánh cơ khí nằm giữa hai số, nhãn phải do người có nghiệp vụ xác nhận; không đổi đáp án đã lưu chỉ vì OCR bất đồng.

## Hiệu năng và cô lập

Trọng số tải lúc build, nạp một lần trong tiến trình reader; không khởi tạo lại cả model cho mỗi ảnh. Hai reader chạy song song; upload/job bất đồng bộ tách API khỏi OCR. Reader không truy cập database, không gắn volume ảnh và không publish cổng host. Trong runtime, mạng dữ liệu internal, filesystem chỉ đọc.

Reader PARSeq chỉ gắn kho model **chỉ đọc**. Kiểm tra đường dẫn, SHA-256, metadata kiến trúc, tên/kích thước/kiểu tensor và tính hữu hạn trước thay trọng số; chuyển về pretrained khi yêu cầu đối chứng. Runtime ghi nhận phiên bản bộ đọc và định vị. Khi bộ định vị trả vùng học hợp lệ, bỏ OCR toàn cảnh dư thừa; vẫn đọc mã khách hàng bằng crop riêng. Không dùng nhãn/vùng thật làm đầu vào kiểm định toàn quy trình.

Thời gian người dùng đợi gồm hàng đợi, giải mã, định vị/OCR mã, crop, reader, database và mạng; không dùng thời gian đọc crop để quảng bá độ trễ toàn pipeline. Xem [tác vụ](jobs.md), [chính sách độ tin cậy](ai-reliability.md) và báo cáo [benchmark lịch sử](reports/modern-reader-benchmark-2026-10-01.md).
