# Rà soát hiệu năng và kiến trúc AI — 01/10/2026

> Cập nhật: PP-OCRv6 small và PARSeq-tiny đã thay thế bộ đọc HOG theo cơ chế đồng thuận trong dịch vụ nội bộ riêng. Xem `docs/MODERN_READER_BENCHMARK_20261001.md`.

## Kết luận điều hành

Hệ thống đang vận hành đúng theo kiến trúc bất đồng bộ: API nhận ảnh, lưu dữ liệu và tạo
công việc; worker nhận công việc bằng khóa `SKIP LOCKED`, đọc ảnh, nhận diện và ghi kết
quả để con người kiểm duyệt. Ảnh và nhãn không được gửi ra dịch vụ bên thứ ba.

Điểm nghẽn chính không nằm ở API hay cơ sở dữ liệu mà ở OCR dự phòng. Trước thay đổi,
mỗi ảnh có thể chạy 9 lần Tesseract cho mã khách hàng và 24 lần cho chỉ số, mỗi lần có
thể chờ tối đa 20 giây. Timeout khi đọc mã khách hàng còn có thể làm hỏng cả công việc.

Sau tối ưu, cùng 5 ảnh có nhãn, cùng thứ tự và cùng máy:

| Chỉ số | Trước | Sau | Thay đổi |
|---|---:|---:|---:|
| Trung vị | 21.199 giây | 13.216 giây | giảm 37,7% |
| P95 | 41.287 giây | 14.553 giây | giảm 64,8% |
| Đọc đúng hoàn toàn | 0/5 | 0/5 | không đổi |

Đây là phép đo chẩn đoán trên ảnh đã lưu và lần đầu có cả chi phí khởi tạo OCR; chỉ có
5 ảnh nên không phải benchmark độc lập. Kết quả chỉ chứng minh giới hạn độ trễ hoạt
động đúng, không chứng minh mô hình chính xác hơn.

## Thay đổi đã áp dụng

- Đặt ngân sách tổng 8 giây cho OCR dự phòng mã khách hàng và 8 giây cho chỉ số.
- Timeout mã khách hàng trả kết quả cần kiểm duyệt thay vì làm thất bại công việc.
- Giới hạn Tesseract ở một luồng OpenMP cho mỗi tiến trình; có thể ghi đè bằng biến môi
  trường khi triển khai. Tài liệu Tesseract khuyến nghị `OMP_THREAD_LIMIT=1` cho xử lý
  nhiều ảnh.
- Bỏ một lần OCR lặp sau khi loại ô số thập phân màu đỏ.
- Bỏ nhánh xử lý vùng thủ công không thể chạy tới trong pipeline tự động.
- Ghi thời gian từng giai đoạn và số lượt OCR dự phòng vào kết quả thô để tiếp tục đo.
- Gộp ba truy vấn lấy mô hình đang hoạt động thành một truy vấn, vẫn kiểm tra ngay ở mỗi
  công việc nên không tạo độ trễ kích hoạt do cache TTL.
- Thêm công cụ `python -m ai.tools.benchmark_pipeline --limit N`. Công cụ chỉ đọc dữ liệu,
  không sửa nhãn, công việc hay mô hình và không in tên ảnh/mã khách hàng.

## Rà soát API, cơ sở dữ liệu và frontend

- API `/dashboard` đo trực tiếp trong container có trung vị 11,9 ms và P95 37,5 ms
  trên 40 lần gọi. Cùng phép đo từ Windows qua Docker Desktop/nginx có trung vị 217 ms;
  phần chênh chủ yếu thuộc đường truyền qua lớp ảo hóa, không phải truy vấn ứng dụng.
- Chỉ mục nhận việc được đổi từ `(status, next_retry_at)` sang
  `(status, priority DESC, created_at, next_retry_at)`, khớp thứ tự worker thực sự dùng
  khi khóa công việc với `SKIP LOCKED`.
- Loại sáu B-tree dư thừa trên khóa đã có unique index: ảnh của kết quả AI, mã lô, ảnh
  của chỉ số, ảnh của công việc, session-token hash và username. Unique constraints và
  toàn bộ tính toàn vẹn dữ liệu vẫn được giữ nguyên.
- Khôi phục phiên quản trị từ hai request tuần tự còn một request: `/auth/session` trả
  thêm username đã xác thực. CSRF vẫn dẫn xuất từ cookie HttpOnly và response vẫn
  `no-store`.
- Phần tải thư mục chỉ được nạp khi vào trang Vận hành. Tổng JavaScript entry công khai
  giảm từ 87.687 xuống 82.626 byte chưa nén, tương đương 5,8%.
- Thêm `type: module` cho frontend, loại chi phí parse lại module trong bộ kiểm thử Node.

Migration `20261001_0023` đã chạy thành công trên PostgreSQL. Sau migration, chỉ mục
hàng đợi mới tồn tại và sáu chỉ mục dư không còn tồn tại.

## Trạng thái chất lượng hiện tại

Mô hình HOG/ridge thử nghiệm gần nhất dùng 37 ảnh (30 train, 7 validation), đạt 11/35
chữ số đúng và 0/7 chỉ số đúng hoàn toàn. Ba artifact vẫn ở trạng thái `TESTING`; quyết
định không kích hoạt là đúng. Phép đo tự động trên 5 ảnh ở trên cũng đạt 0/5 trước và
sau tối ưu. Vì vậy nút thắt chất lượng là kiến trúc nhận dạng và dữ liệu, không phải chỉ
là tiền xử lý hoặc tăng số lần gọi OCR.

## Đối chiếu với hướng hiện đại

### Định vị công tơ và vùng số

YOLO26 là bản Ultralytics mới nhất đã phát hành tính đến ngày rà soát; YOLO27 mới ở trạng
thái dự kiến và chưa có weights/package. YOLO26 hỗ trợ detection, pose/keypoints và oriented bounding boxes. Với dữ liệu hiện có
là bốn điểm vùng công tơ và bốn điểm vùng chỉ số, `pose` hoặc `OBB` phù hợp hơn ridge
hồi quy trực tiếp. Tài liệu chính thức báo tốc độ CPU ONNX của bản nano trên COCO, nhưng
đó không phải độ chính xác trên ảnh công tơ. Trọng số COCO cũng không tự biết lớp công
tơ; bắt buộc fine-tune bằng ảnh của dự án. Cần kiểm tra giấy phép AGPL/enterprise trước
khi đưa Ultralytics vào sản phẩm thương mại.

Nguồn: https://docs.ultralytics.com/models/yolo26

### Đọc chuỗi chữ số

PP-OCRv6 (PaddleOCR 3.7.0, phát hành 11/06/2026) có các cỡ tiny 1,5M, small 7,7M và
medium 34,5M tham số; nhóm phát triển công bố cải thiện riêng cho chữ công nghiệp và
màn hình số. Đây là ứng viên ưu tiên để chạy benchmark cục bộ, nhưng số liệu công bố
không thể thay thế phép đo exact-match trên công tơ cơ khí của dự án.

Nguồn: https://github.com/PaddlePaddle/PaddleOCR/releases/tag/v3.7.0

PARSeq là mô hình nhận dạng cả chuỗi, có pretrained và hỗ trợ fine-tune/tập ký tự tùy
chỉnh. Cách đọc chuỗi phù hợp hơn bộ phân loại từng ô HOG hiện tại vì không cần giả định
ranh giới ô số hoàn hảo. Đây là baseline nghiên cứu tốt, nhưng không phải mô hình mới
nhất năm 2026 và cần benchmark cùng PP-OCRv6.

Nguồn: https://github.com/baudm/parseq

### Bài toán công tơ tương tự

UFPR-AMR dùng pipeline hai giai đoạn: phát hiện vùng bộ đếm rồi nhận dạng; bộ dữ liệu có
2.000 ảnh gắn nhãn thủ công và dùng augmentation cân bằng. Điều này củng cố hướng tách
localization và sequence recognition của dự án, đồng thời cho thấy 37 ảnh hiện tại quá
ít để kết luận mô hình tổng quát.

Nguồn: https://arxiv.org/abs/1902.09600

## Kiến trúc đích đề xuất

1. Chuẩn hóa ảnh nhẹ, giữ nguyên ảnh gốc.
2. YOLO26n-pose/OBB hoặc detector tương đương được fine-tune để tìm công tơ và bốn góc
   vùng chỉ số.
3. Biến đổi phối cảnh vùng chỉ số.
4. PP-OCRv6 small làm baseline chính; PARSeq-tiny là mô hình đối chứng. Tập ký tự chỉ
   gồm 0–9, bỏ ô đỏ cuối cùng ở bước crop/nhãn.
5. Đối chiếu mã khách hàng với database và kiểm tra logic theo tháng: số mới không nhỏ
   hơn số trước nếu công tơ không thay.
6. Hiệu chỉnh confidence trên tập validation độc lập; chỉ tự xác nhận khi ngưỡng đạt tỷ
   lệ lỗi đã thống nhất. Không dùng confidence thô của OCR như xác suất đúng.

## Điều kiện trước khi thay mô hình sản xuất

- Tách tập test theo công tơ/khách hàng, không tách ngẫu nhiên các ảnh cùng công tơ.
- Tối thiểu vài trăm ảnh đa dạng góc chụp, ánh sáng, loại mặt kính và trạng thái bánh số;
  tiếp tục active learning cho các ca confidence thấp.
- Báo cáo `exact reading accuracy`, character error rate, coverage/abstention, mAP hoặc
  sai số bốn góc, P50/P95 và bộ nhớ trên đúng máy triển khai.
- Chạy mô hình mới ở shadow mode, không tự ghi nhận số điện; chỉ kích hoạt nếu vượt mô
  hình hiện tại trên tập test khóa và không làm tăng tỷ lệ tự xác nhận sai.
- Export ONNX rồi benchmark OpenVINO/CPU. ONNX Runtime lưu ý số luồng mặc định theo số
  lõi vật lý; cấu hình luồng phải đo trên đúng phần cứng, không sao chép số benchmark từ
  nhà cung cấp.

Nguồn ONNX Runtime: https://onnxruntime.ai/docs/performance/tune-performance/threading.html

## Phạm vi kiểm thử

- Backend: 130 kiểm thử đạt.
- AI: 30 kiểm thử đạt trong container cùng dependency production.
- Ruff: đạt trên toàn bộ file AI đã thay đổi.
- Frontend: typecheck, lint, build production và 7 kiểm thử đạt.
- Backend health: HTTP 200; backend healthy; worker và trainer đang chạy.
