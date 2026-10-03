# Dữ liệu và huấn luyện

Ảnh và nhãn được lưu trong PostgreSQL/volume riêng, không commit vào source code. Một mẫu chỉ đủ điều kiện sau khi con người xác nhận số điện, vùng bốn góc chỉ số và vùng bốn góc toàn bộ công tơ.

Khi số mẫu đạt `training_min_samples` (mặc định 200) và có đủ mẫu mới, trainer tự tạo phiên huấn luyện. Dataset được sắp xếp, loại trùng theo SHA-256 và chia train/validation ổn định theo đồng hồ để hạn chế rò rỉ dữ liệu.

Trainer chỉ huấn luyện hai model định vị nhẹ:

- `meter_locator_ridge`: bốn góc mặt công tơ.
- `reading_region_ridge`: bốn góc vùng bộ số.

Artifact `.npz` không dùng pickle, được kiểm tra SHA-256 và đăng ký ở trạng thái `TESTING`. Chỉ model có độ chính xác vùng validation từ 80% mới được kích hoạt. Worker kiểm tra lại checksum trước khi nạp model cho tác vụ tiếp theo.

Tầng đọc chuỗi không còn dùng HOG từng ô. PP-OCRv6 small và PARSeq-tiny dùng trọng số dựng sẵn và đọc cả chuỗi sau hiệu chỉnh phối cảnh. Dữ liệu mới trước hết dùng để đánh giá exact-match, coverage, precision khi có kết quả và hiệu chỉnh chính sách đồng thuận. Fine-tune deep model chỉ nên thực hiện khi có tập train/test độc lập đủ lớn và tài nguyên GPU phù hợp; hệ thống không giả vờ huấn luyện deep model từ vài ảnh.

Mỗi phiên huấn luyện tạo thêm `sequence_datasets/<version>` trong volume mô hình. Thư mục chỉ chứa crop dãy số đã hiệu chỉnh phối cảnh, `train.tsv`, `validation.tsv` và manifest SHA-256; ảnh gốc không bị sao chép. Trainer sau đó gửi tập validation qua cả PP-OCRv6 và PARSeq, ghi exact-match, coverage và character error rate vào model registry. Nếu dịch vụ đọc không khả dụng, phiên huấn luyện định vị vẫn hoàn tất nhưng kết quả ghi rõ benchmark chưa thực hiện.

Quy trình vận hành: tải ảnh → khoanh vùng công tơ/vùng chỉ số nếu tự động sai → xác định chỉ số → sửa kết quả → xác nhận tháng → theo dõi dataset và phiên huấn luyện tại **Vòng đời mô hình**. Mọi thay đổi nhãn đều có log trước/sau.
