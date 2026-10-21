# Đối chứng định vị học sâu và đo tốc độ OCR

## Phạm vi và sử dụng

SUPER_ADMIN vào Vòng đời mô hình → Huấn luyện, bật **Học MobileNetV3 và so sánh định vị với Ridge**. Có thể bỏ fine-tune reader để đo riêng định vị. Mặc định 40 epoch; phiên tự động không mặc nhiên thêm ứng viên. Giữ nguyên xác minh/phân tập/ngưỡng của phiên tiêu chuẩn; ít dữ liệu chỉ chẩn đoán, không kích hoạt.

MobileNetV3-small pretrained ImageNet là ứng viên CPU nhẹ, không phải tuyên bố detector mới nhất/tốt nhất. Backbone cố định, MLP học tám tọa độ của một công tơ trên ảnh và vùng số trong mặt công tơ chỉnh phối cảnh. Đây là định vị bốn góc một đối tượng, không phải YOLO nhiều đối tượng. Worker chạy ONNX, không cần Torch.

Phiên huấn luyện mới dùng kiến trúc v2: đầu vào 320×320, lưới đặc trưng 5×5, loss chuẩn hóa theo chiều rộng/cao vùng để quan tâm đến dãy số mỏng. Epoch chọn theo IoU validation; không dùng holdout. Runtime vẫn đọc đúng contract v1 192 px của artifact cũ, không đổi nội dung artifact đã lưu.

Bộ vùng số học thêm crop theo khung công tơ dự đoán và hai nhiễu bốn góc nhỏ chỉ trong train. Nhãn vùng số được biến đổi cùng crop; không sửa nhãn trong DB. Validation của bộ vùng số dùng khung công tơ dự đoán, không cung cấp vùng công tơ thật; giảm lệch điều kiện giữa học và chạy. Các crop tăng cường không được đếm thành ảnh/người dùng mới. Benchmark vẫn phải đo IoU toàn luồng trên ảnh gốc; IoU trong mặt phẳng chỉnh phối cảnh không thay thế con số này.

Kho mô hình → **So sánh Ridge / MobileNetV3**: cùng snapshot, validation/holdout, số mẫu, IoU công tơ/vùng số và p95 định vị. Đầu định vị chọn epoch bằng validation, không dùng holdout chọn epoch. IoU toàn luồng định vị không cung cấp vùng thật cho suy luận; đánh giá conditional có vùng công tơ thật không gọi là toàn luồng.

Ngoài tất cả gate cũ, ứng viên học sâu phải tăng IoU vùng tương ứng nghiêm ngặt, không giảm exact-match/coverage so với Ridge trên cùng holdout độc lập đã đánh giá đầy đủ. Không holdout/xác minh nhóm thì khóa; không tự chọn/activate bằng điểm validation đẹp. Kích hoạt công tơ trước vùng số, cùng phiên/kiến trúc. Đổi kiến trúc lưu trữ vùng số/reader không tương thích. Reader fine-tune hiện được kiểm định với cặp Ridge, không tự chuyển bằng chứng sang cặp MobileNetV3.

## PARSeq ONNX và đóng gói

Encoder ONNX có đầu vào cố định `[1,3,32,128]`; decoder tự hồi quy/refinement vẫn dùng PARSeq đã pin. Không trace decoder dừng sớm theo một ảnh rồi giả vờ graph tổng quát. FP32, chưa INT8. Kiểm tra checksum graph/hash encoder, tương đương số học/chuỗi; checkpoint đổi encoder không được dùng graph không khớp.

Mặc định vẫn Torch: không mặc nhiên ONNX nhanh hơn. Benchmark nhiều vòng cùng ảnh, đảo thứ tự hai runtime giữa các vòng. Chỉ thay runtime sau phép đo đủ đại diện chứng minh nhanh hơn và không đổi kết quả. `encoder_runtime` là enum nội bộ, không cho đường dẫn tùy ý/endpoint public. Session ONNX mới tắt telemetry; dịch vụ vẫn mạng nội bộ/filesystem chỉ đọc.

NumPy reader/trainer 1.26.x để tương thích Torch 2.2 đã đóng gói. `TORCH_HOME` trỏ cache trong image, độc lập `XDG_CACHE_HOME=/tmp/.cache` của trainer. Không cần Internet lúc nhận diện/huấn luyện.

## Benchmark ảnh thật, không sửa nghiệp vụ

Chạy khi không có upload/train khác nếu muốn đo nhàn rỗi:

```text
docker exec elec_man-worker-1 python -m ai.tools.benchmark_pipeline --limit 10 --repeats 3 --mode selected --compare-encoder --output /tmp/encoder-selected.json
python scripts/copy_runtime_report.py --name encoder-selected.json
docker exec elec_man-worker-1 python -m ai.tools.benchmark_pipeline --limit 5 --repeats 3 --mode automatic --output /tmp/automatic-latency.json
python scripts/copy_runtime_report.py --name automatic-latency.json
```

Report JSON phải mới, không ghi đè; chỉ dưới MODELS_ROOT/thư mục tạm. Worker gắn model chỉ đọc nên dùng `/tmp` hoặc bỏ `--output` xem summary. Script dùng cấu hình gốc container, không nhận URL/DSN khác; **không dùng `.env.example` kết nối database thật**. Kiểm tra SHA ảnh/trạng thái nhãn. Không sửa DB, nhãn, chỉ số tháng, job/activation.

`selected` dùng vùng/số chữ số do người lưu, khác tự động toàn ảnh. `automatic` không đưa vùng/số chữ số từ nhãn. Cả hai là chẩn đoán ảnh đã dùng phát triển, không là holdout độc lập. Vòng đầu giữ trong report, loại khỏi summary warm. Report có hash/đề xuất số/timing, không chứa ảnh/địa chỉ/secret; không tự công khai report hoặc dữ liệu mới.

Timing pipeline: decode, tiền xử lý, chất lượng, định vị công tơ/vùng số, OCR cảnh, OCR khách hàng, crop, đọc số, kiểm tra. Client đo PNG encode/RPC; service đo decode/strip/chờ khóa/predict. Reader song song: không cộng RPC vào tổng lần nữa. Giám sát tách tự động/thủ công trên tối đa 500 kết quả lưu; không suy đoán timing thiếu. Benchmark không lưu AI result nên không tự thêm số liệu vào Giám sát.

## Tối ưu OCR khách hàng

Tái sử dụng dòng OCR cảnh; hỗ trợ mã có cấu trúc như PN2.001, PN.001 và UB.001 kể cả khi OCR tách khoảng trắng quanh dấu chấm. Không rút PN2 thành PN, không fuzzy-match/đoán lại mã. Bỏ các tiền tố thông số thông dụng như No./rev khi không có nhãn khách hàng. Mã mâu thuẫn phải kiểm tra thủ công. Kết quả vẫn phải đối chiếu mã chuẩn trong database trước xác nhận; việc trích được mã không chứng minh mã đó đúng.

Nếu định vị học đã bỏ OCR toàn cảnh, chỉ OCR crop khách hàng. Tesseract fallback tối đa bốn lượt, ngân sách mặc định tổng 3 giây (trước đây 6 lượt/8 giây). Hết thời gian thì chuyển kiểm tra thủ công, không đoán mã; ảnh khó có thể cần người nhập mã. RapidOCR giới hạn hai pool ORT một thread để tránh tranh CPU.

OCR khách hàng chạy song song với đọc chuỗi số, không chia sẻ session DB giữa thread. Kết quả job chỉ trả khi cả hai hoàn tất, không phải tính năng streaming kết quả sớm. `customer_ocr` là thời lượng nhánh khách hàng; `customer_wait` là thời gian còn phải chờ sau khi đọc số; các thời lượng chồng nhau không được cộng thành tổng. Luồng khoanh vùng thủ công vẫn bỏ toàn bộ OCR khách hàng.

Benchmark có số lượt tìm được mã/hết ngân sách nhưng chưa có nhãn mã khách hàng đủ để đo accuracy; trường `customer_accuracy_evaluated=false` thể hiện rõ giới hạn này.

## Kiểm thử offline

```text
docker run --rm --network none --read-only --env XDG_CACHE_HOME=/tmp/.cache --tmpfs /tmp:size=256m,mode=1777 --cap-drop ALL --security-opt no-new-privileges:true elec_man-trainer python -m ai.tools.smoke_locator_onnx
```

Học thật trên ảnh tổng hợp, export/inference ONNX, encoder Torch/ONNX và từ chối hash không tương thích; không chứng minh accuracy hoặc SLA trên ảnh thực.

Nguồn: [TorchVision MobileNetV3-small](https://docs.pytorch.org/vision/stable/models/generated/torchvision.models.mobilenet_v3_small.html), [PARSeq](https://github.com/baudm/parseq), [ONNX Runtime quantization](https://onnxruntime.ai/docs/performance/model-optimizations/quantization.html). Quantization có thể giảm accuracy; không bật chỉ vì file nhỏ.
