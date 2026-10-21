# Đối chứng định vị học sâu và đo tốc độ OCR

## Phạm vi và sử dụng

SUPER_ADMIN vào Vòng đời mô hình → Huấn luyện, bật **Học MobileNetV3 và so sánh định vị với Ridge**. Có thể bỏ fine-tune reader để đo riêng định vị. Mặc định 40 epoch; phiên tự động không mặc nhiên thêm ứng viên. Giữ nguyên xác minh/phân tập/ngưỡng của phiên tiêu chuẩn; ít dữ liệu chỉ chẩn đoán, không kích hoạt.

MobileNetV3-small pretrained ImageNet là ứng viên CPU nhẹ, không phải tuyên bố detector mới nhất/tốt nhất. Backbone cố định, MLP học tám tọa độ của một công tơ trên ảnh và vùng số trong mặt công tơ chỉnh phối cảnh. Đây là định vị bốn góc một đối tượng, không phải YOLO nhiều đối tượng. Worker chạy ONNX, không cần Torch.

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

## Kiểm thử offline

```text
docker run --rm --network none --read-only --env XDG_CACHE_HOME=/tmp/.cache --tmpfs /tmp:size=256m,mode=1777 --cap-drop ALL --security-opt no-new-privileges:true elec_man-trainer python -m ai.tools.smoke_locator_onnx
```

Học thật trên ảnh tổng hợp, export/inference ONNX, encoder Torch/ONNX và từ chối hash không tương thích; không chứng minh accuracy hoặc SLA trên ảnh thực.

Nguồn: [TorchVision MobileNetV3-small](https://docs.pytorch.org/vision/stable/models/generated/torchvision.models.mobilenet_v3_small.html), [PARSeq](https://github.com/baudm/parseq), [ONNX Runtime quantization](https://onnxruntime.ai/docs/performance/model-optimizations/quantization.html). Quantization có thể giảm accuracy; không bật chỉ vì file nhỏ.
