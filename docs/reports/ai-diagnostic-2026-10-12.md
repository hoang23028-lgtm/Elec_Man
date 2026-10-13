# Chẩn đoán AI ngày 12/10/2026

> Báo cáo lịch sử theo ngày, không phải hướng dẫn bản hiện hành. Xem [danh mục tài liệu](../README.md).

## Vì sao giao diện hiển thị 0%?

Đọc bản ghi TrainingRun gần nhất trong database (không sửa dữ liệu):

- Thời điểm: 01/10/2026, 20:21:42 giờ Việt Nam.
- Thuật toán: `four-stage-region-ridge-hog-softmax-v3`, mô hình cũ.
- 30 ảnh huấn luyện, 7 ảnh kiểm định, 35 chữ số kiểm định.
- Đúng từng chữ số: 31,43%; đúng toàn chuỗi: 0%.
- Phạm vi: `ground_truth_crop_and_digit_count`; không phải toàn quy trình.
- Mô hình thử nghiệm, số mẫu thấp hơn ngưỡng cấu hình 200.

Vì vậy 0% không phải số đo của PP-OCR/PARSeq hiện đang chạy. Metrics lưu lại cho
thấy mô hình cũ nhận dạng yếu ngay cả khi biết vùng và số chữ số; chưa đủ bằng
chứng để quy nguyên nhân duy nhất cho ảnh mờ, nhãn sai hoặc thiếu dữ liệu.

## Kiểm tra suy luận hiện tại

Hai endpoint nội bộ `/health/ready` đều trả `ready`. Chạy từ worker qua
ConsensusMeterReader; đọc dữ liệu bằng `load_validation_samples`, crop phối cảnh
từ nhãn người dùng, gửi crop đến hai dịch vụ trong mạng Docker nội bộ. Không train,
không đăng ký/kích hoạt mô hình, không lưu kết quả vào bảng nghiệp vụ.

| Ảnh kiểm định theo thứ tự tập chia | PP-OCR | PARSeq | Kết quả đồng thuận | Thời gian (ms) |
|---|---|---|---|---:|
| 1 | Không trả chuỗi hợp lệ | Không trả chuỗi hợp lệ | Cần kiểm duyệt | 3228 |
| 2 | Đúng | Đúng | Đúng | 1738 |
| 3 | Không trả chuỗi hợp lệ | Sai | Cần kiểm duyệt | 690 |
| 4 | Đúng | Đúng | Đúng | 966 |
| 5 | Đúng | Đúng | Đúng | 832 |
| 6 | Đúng | Đúng | Đúng | 856 |
| 7 | Đúng | Đúng | Đúng | 576 |

- Đúng toàn chuỗi: 5/7 (71,4%).
- Tỷ lệ trả lời: 5/7 (71,4%); còn 2/7 không trả chỉ số tự động.
- Đúng trong các câu trả lời: 5/5. Không suy rộng thành độ chính xác 100%.
- Trung vị thời gian: 856 ms; khoảng 576–3228 ms. Chỉ một lượt chạy, có thể gồm
  chi phí làm nóng; không phải benchmark tải hoặc cam kết thời gian đáp ứng.

## Giới hạn và bước tiếp theo

- Chỉ có 7 mẫu, dùng vùng và số chữ số đúng đã biết; chưa đo định vị tự động.
- Không khẳng định tập này trùng hệt tập kiểm định của lần huấn luyện cũ.
- Khi chưa có mã/nhóm công tơ, hàm chia dùng hash ảnh: hai ảnh khác nhau của cùng
  công tơ vẫn có thể nằm ở hai tập. Chưa bảo đảm độc lập theo công tơ.
- Pipeline hiện huấn luyện bộ định vị Ridge, xuất dữ liệu crop và benchmark bộ
  đọc pretrained; `sequence_reader_trainable=False`. Thêm ảnh rồi chạy pipeline
  hiện tại không tự fine-tune PP-OCR/PARSeq.
- Chưa sửa cấu hình, ngưỡng hay metrics lịch sử. Tự động xác nhận vẫn bị chặn.
- Tiếp theo: kiểm tra hai mẫu không trả lời, xác thực nhóm công tơ để chia dữ liệu,
  sau đó đo riêng phần định vị và đọc chuỗi trên tập kiểm định cố định.

## Đối chiếu định vị tự động cùng ngày

Chạy `current_pipeline().process(path)` trên cùng 7 mẫu, không truyền nhãn vùng
hoặc số chữ số. Runtime báo `modern-sequence-consensus-v1`, `has_meter_model=False`,
`has_region_model=False`: chưa có bộ định vị đã huấn luyện được kích hoạt.
Cả 7 ảnh dùng nguồn vùng chỉ số `SCENE_OCR`.

| Mẫu | Nhãn đang lưu | Kết quả tự động | IoU hộp vùng chỉ số so với nhãn | Thời gian (ms) |
|---|---|---|---:|---:|
| 1 | 20148 | Không trả lời | 0,000 | 6292 |
| 2 | 35883 | Không trả lời | 0,000 | 3960 |
| 3 | 95106 | Không trả lời | 0,000 | 6230 |
| 4 | 14576 | Không trả lời | 0,045 | 7060 |
| 5 | 26436 | 26436 | 0,576 | 7939 |
| 6 | 01338 | 00177 | 0,000 | 7599 |
| 7 | 03872 | Không trả lời | 0,026 | 4450 |

IoU ở đây là giao/hợp của hộp bao trục song song, không phải IoU đa giác. Kết quả:
1/7 đúng, 1/7 sai, 5/7 không trả lời. Hai bộ đọc đồng thuận không bảo đảm đúng nếu
crop đầu vào là vùng sai. Giữ chặn tự động xác nhận; chưa thay đổi ngưỡng.

Thời gian trung vị 6292 ms. Riêng tầng định vị + OCR mã khách hàng mất 2337–6728 ms;
OCR toàn cảnh mất 888–2022 ms; crop/đọc chỉ số mất 66–313 ms trong lượt chạy này.
Đây là đo chẩn đoán một lượt, không phải benchmark tải; chưa tách riêng thời gian
định vị khỏi OCR mã khách hàng.

### Hai ảnh cần xem lại

- Mẫu 1: ảnh gốc có phản chiếu/vệt ngang qua dãy số; cả hai bộ đọc không trả chuỗi
  hợp lệ ngay cả với vùng người dùng. Không kết luận nhãn sai chỉ vì OCR thất bại.
- Mẫu 3: nhãn lưu `95106`, PARSeq trả `95109`, PP-OCR không trả chuỗi hợp lệ.
  Người dùng đã xác nhận đúng là `95106`: bánh số cuối đang chuyển từ 6 lên 7.
  Nhận định thị giác ban đầu nghiêng về `95109` là không đúng. Giữ nhãn `95106`,
  đánh dấu đây là tình huống chuyển số cơ học trong báo cáo; không sửa database.

Hai bản sao ảnh gốc dùng để quan sát nằm trong `.codex-tmp/ai-diagnostic-20261012/`;
không sửa ảnh gốc trong storage. Không huấn luyện hoặc kích hoạt mô hình trong lượt này.

Ưu tiên kế tiếp: sửa/đánh giá bước chọn vùng chỉ số
trên tập kiểm định cố định. Không kích hoạt mô hình cũ hoặc bỏ cơ chế kiểm duyệt
chỉ để tăng số ảnh trả lời.

## Thử bản sửa chọn vùng theo ngữ cảnh kWh

Source `ai/pipeline/localization.py` được sửa để ưu tiên dòng chỉ số chứa `kWh`
hoặc nằm sát bên trái ký hiệu `kWh` trên cùng hàng; loại các dòng vòng/kWh,
số sản xuất, serial và mã PDM. Chỉ thay thứ tự chọn ứng viên, không tăng confidence
và không sử dụng nhãn đáp án. Đây vẫn là heuristic, chưa thay thế mô hình định vị.

Thử bằng cách nạp source mới vào một tiến trình Python riêng trong container worker;
không ghi đè file trong container, không thay worker chính, không ghi kết quả nghiệp vụ.

| Mẫu | Trước sửa | Sau sửa |
|---|---|---|
| 1 | Không trả lời | Không trả lời |
| 2 | Không trả lời | Không trả lời |
| 3 | Không trả lời | Không trả lời |
| 4 | Không trả lời | Không trả lời |
| 5 | 26436, đúng | 26436, đúng |
| 6 | 00177, sai | 01338, đúng |
| 7 | Không trả lời | Không trả lời |

Kết quả chẩn đoán tăng từ 1/7 lên 2/7 đúng, không có câu trả lời sai trong lượt
7 mẫu này. Không suy rộng ra dữ liệu chưa xem: các mẫu này đã được dùng để phân
tích bản sửa, không còn là tập kiểm định độc lập cho lựa chọn thuật toán.
Không so sánh tốc độ hai lượt vì có chạy kiểm thử khác đồng thời.

34 kiểm thử AI đạt trong container kiểm thử không có mạng, mount source chỉ đọc;
Ruff check/format của hai file sửa/thêm đạt. Python host thiếu OpenCV nên dùng
container có dependency sẵn, không cài thêm lên máy người dùng.
Bản sửa chỉ có trong source, chưa build/deploy worker. Bước tiếp: cải thiện crop
phối cảnh và đánh giá trên dữ liệu bổ sung độc lập, vẫn giữ kiểm duyệt bắt buộc.

### Thử nghiệm làm thẳng vùng OCR: không giữ trong pipeline

Thử giữ bốn góc của dòng OCR, mở rộng theo trục của dòng rồi crop phối cảnh.
Đánh giá trên cùng 7 ảnh vẫn chỉ đúng mẫu 5 và 6 (2/7), 5 ảnh không trả lời.
36 test của bản thử đạt nhưng chất lượng nhận diện không tăng. Đã bỏ thay đổi
crop này khỏi pipeline; giữ bản chọn vùng theo ngữ cảnh kWh của lượt trước.
Giữ thêm test biên ảnh cho cơ chế padding hiện có.

Không triển khai, không sửa nhãn và không thay đổi mô hình đang chạy. Kết quả
cho thấy làm thẳng một vùng OCR chưa đúng/chứa thêm ký hiệu chưa đủ; cần đánh giá
bộ định vị chuyên biệt, cùng tập ảnh chưa dùng để chọn thuật toán. Không tiếp tục
tinh chỉnh ngưỡng chỉ để làm đẹp điểm trên 7 ảnh đã biết.
