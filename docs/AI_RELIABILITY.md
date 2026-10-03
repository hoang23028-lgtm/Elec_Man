# Kiểm soát độ tin cậy AI

## Chính sách hiện tại

- OCR chỉ đề xuất. Mọi kết quả phải được người dùng xác nhận; điểm trên 90% không tự tạo bản ghi chính thức.
- Khi xác nhận lần đầu, chọn kỳ ghi điện rõ ràng. Không suy luận kỳ tháng từ ngày tải ảnh hoặc ngày xác nhận.
- Sửa kết quả đã xác nhận giữ nguyên kỳ cũ nếu không gửi kỳ mới. Không ghi đè ngầm một ảnh khác của cùng khách hàng/tháng.
- Nhận diện lại không ghi đè nhãn `LABELED`, chỉ số đã xác nhận hoặc quyết định từ chối. Vùng thử nghiệm không thay vùng nhãn đã lưu; muốn thay nhãn phải bấm Lưu/Cập nhật nhãn AI.
- Các chỉ số validation hiện tại đo trên vùng và số chữ số đã biết. Điểm vùng là phép quy đổi sai số tọa độ, không phải tỷ lệ phát hiện đúng.

## Kiểm thử trước khi vận hành tự động

1. Chuẩn bị ảnh có vùng công tơ, bốn góc vùng chỉ số và chuỗi chỉ số nguyên được kiểm tra thủ công. Không dùng kết quả OCR làm nhãn chuẩn chưa kiểm duyệt.
2. Giữ riêng tập kiểm thử không dùng huấn luyện hoặc chọn mô hình. Tách theo công tơ/khách hàng để tránh cùng công tơ xuất hiện ở cả train và test; với ảnh chưa có mã, cần gán nhóm trước khi chia.
3. Đo bộ đọc trên vùng chuẩn để tách lỗi đọc số khỏi lỗi định vị.
4. Đo toàn bộ quy trình trên ảnh gốc, không truyền vùng hoặc độ dài nhãn. Báo cáo đúng toàn chuỗi, sai từng chữ số, không đọc được, lỗi định vị, thời gian xử lý; phân nhóm phản sáng, nghiêng, mờ và loại công tơ.
5. Đánh giá riêng các trường hợp có điểm cao nhưng sai. Chọn ngưỡng theo tỷ lệ sai trong nhóm được tự động chấp nhận, không theo tên gọi “độ tin cậy”.
6. Chạy thử có người kiểm duyệt, lưu phiên bản mô hình và dữ liệu đánh giá. Chỉ xây chính sách tự động xác nhận sau khi có bằng chứng trên tập kiểm thử độc lập.

Unit test và ảnh tổng hợp chỉ xác nhận hợp đồng phần mềm, không chứng minh độ chính xác trên ảnh thực tế. Phiên bản này chưa thay thế các mô hình cơ sở bằng mạng học sâu và chưa thực hiện đánh giá thực địa.

## Kiểm thử mã nguồn

- Backend: `python -m pytest backend/tests -q` (môi trường có backend và dependency kiểm thử).
- AI: `python -m pytest ai/tests -q` (môi trường có OpenCV, RapidOCR và dependency AI).
- Frontend: chạy `npm run typecheck`, `npm run lint`, `npm run build` trong thư mục frontend.
- Trước triển khai: dùng bản phát hành cố định, kiểm tra HTTPS, phân quyền API, khôi phục backup và thông tin khách hàng hiển thị công khai.
