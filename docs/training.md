# Gắn nhãn, huấn luyện và kiểm định mô hình

## Những gì đã tích hợp

Có thêm tùy chọn đối chứng định vị MobileNetV3-small với Ridge trong cùng phiên, xuất ONNX và khóa kích hoạt khi chưa tăng chất lượng trên holdout. Xem [định vị và hiệu năng](locator-and-latency.md); phiên tự động mặc định không chạy thêm ứng viên.

SUPER_ADMIN có thể chuẩn bị phân tập, chạy phiên học, fine-tune PARSeq-tiny, xem tiến trình/hủy và kích hoạt ứng viên đạt gate. ADMIN làm nghiệp vụ và gắn nhãn; VIEWER chỉ xem. Upload ảnh **không** tự tạo nhãn đúng hoặc bảo đảm mô hình chính xác.

Trainer học hai bộ định vị Ridge (không phải deep detector): mặt công tơ trên toàn ảnh, vùng số trong mặt công tơ đã chỉnh phối cảnh. Bộ đọc PARSeq-tiny được học có giám sát bằng teacher forcing tự hồi quy, cập nhật decoder/head và giữ encoder pretrained. Đây là một cách thích nghi dùng ít tài nguyên, không phải bản sao toàn bộ thuật toán huấn luyện permutation của bài PARSeq. PP-OCRv6 small và PARSeq pretrained vẫn làm đối chứng.

## 1. Lưu nhãn ở Vận hành

1. Upload và xử lý ảnh.
2. Khoanh bốn góc toàn công tơ, rồi vùng các bánh số nguyên. Vùng số phải nằm trong vùng công tơ, không chứa bánh đỏ.
3. Nhập **chuỗi số đúng**, giữ số 0 đầu (ví dụ `00120`), bỏ phần sau dấu phẩy. Kiểm tra kỹ bánh đang chuyển số; không tự đổi đáp án để hợp với OCR.
4. Lưu nhãn. Chưa có mã khách hàng vẫn có thể LABELED để học, không cần tạo chỉ số tháng.

Mẫu đủ nhãn cần trạng thái LABELED/CONFIRMED, người đã lưu chỉ số và hai vùng, 4–8 chữ số ASCII và hai polygon hợp lệ. Ảnh tải mới, bị từ chối hoặc chỉ có đề xuất AI không được coi là nhãn con người.

## 2. Xác minh nhóm và phân tập

Mở **Vòng đời mô hình → Dữ liệu huấn luyện**. Chọn Kiểm tra trên mỗi ảnh; xem ảnh lớn và nhãn số, sửa nhãn/vùng tại Vận hành nếu cần. Nhập mã nhóm như `CT001` khi chưa biết mã khách hàng; cùng công tơ trong nhiều ảnh/tháng phải dùng cùng nhóm. Mã nhóm được trim/viết hoa, không cho đường dẫn/ký tự tùy ý.

Đánh dấu đã xác minh định danh công tơ và đã kiểm tra nhãn/hai vùng. Phân tập:

| Phân tập | Dùng làm gì | Lưu ý |
|---|---|---|
| Huấn luyện (TRAIN) | Cập nhật trọng số | Không chứa ảnh/nhóm của hai tập còn lại |
| Chọn trọng số (VALIDATION) | Chọn epoch tốt nhất, đánh giá định vị và reader | Không phải test độc lập cuối cùng |
| Kiểm tra độc lập (HOLDOUT) | Chỉ đánh giá sau chọn trọng số | Khóa ngay khi lưu, không chuyển sang học/đổi nhóm |
| Chưa phân tập | Chưa đủ xác minh | Không vào phiên tiêu chuẩn |

Nên dành holdout từ công tơ chưa dùng để phát triển; ảnh từng dùng để điều chỉnh thuật toán không thể trở thành test hoàn toàn mới chỉ bằng đổi dropdown. Cần thêm ảnh thực tế độc lập. Có thể bắt đầu với tỷ lệ nhóm 70/15/15, nhưng ưu tiên đủ độ đa dạng và số mẫu hơn một tỷ lệ cứng.

Server nối nhóm qua SHA-256 ảnh, mã khách hàng chuẩn, UUID khách hàng và nhóm thủ công. Ảnh trùng chỉ tính một lần. Cùng nhóm vào hai tập bị từ chối, kể cả khi có ảnh chưa xác minh. Nếu sửa nhãn/vùng sau xác minh, revision thay đổi: ảnh không còn được dùng trong phiên tiêu chuẩn cho đến khi kiểm tra lại. Ghi log đầy đủ trước–sau, kiểm tra revision chống ghi đè.

## 3. Tạo phiên

Mở **Huấn luyện**. Xem số train/validation/holdout, lỗi dữ liệu và ngưỡng. Ngưỡng mặc định 200 mẫu **train + validation đã xác minh**, không cộng holdout. Tối thiểu kỹ thuật 2 train + 1 validation chỉ để chương trình chạy, không chứng minh đủ chất lượng.

Bật Fine-tune PARSeq-tiny (mặc định bật); bắt đầu với 10 epoch, batch 8, learning rate 0,0001. Server giới hạn 1–100 epoch, batch 1–64, learning rate (0; 0,01]. Giảm batch nếu thiếu RAM. Chọn bỏ fine-tune để kiểm tra hai bộ định vị/reader cơ sở trước. Xác nhận tạo phiên, theo dõi stage/epoch/loss.

**Chạy chẩn đoán** cho phép ít mẫu, có thể chia nhóm chưa xác minh theo hash để thử phần mềm. Holdout đã đặt trước vẫn không vào train; mọi kết quả chẩn đoán đều không được kích hoạt. Không dùng chế độ này để công bố độ chính xác sản xuất.

Nhãn/phân tập được đóng băng thành snapshot JSON có SHA-256 khi enqueue. Trainer không lấy các nhãn vừa sửa trong lúc phiên đang chạy. File ảnh/crop phải khớp checksum; file thay đổi làm phiên thất bại. Chỉ một phiên PENDING/RUNNING; phiên FAILED/CANCELLED dừng tự train cho đến khi sửa nguyên nhân và hoàn tất một phiên mới. Hủy được kiểm tra từng lô học/stage, không phải ngắt tức thời một HTTP inference đang chạy.

## 4. Artifact và đánh giá

- Hai bộ định vị: NPZ, `allow_pickle=False`; vùng số có metadata `coordinate_space=meter`.
- PARSeq đã học: `parseq_tiny_finetuned/<version>/model.safetensors`, có SHA-256 và kiến trúc/base revision đóng gói.
- `sequence_datasets/<version>/`: crop phối cảnh, train.tsv, validation.tsv, holdout.tsv, manifest SHA-256. Không nhân bản toàn ảnh gốc.
- Validation chọn epoch tốt nhất theo exact-match, rồi CER. **Holdout không dùng chọn epoch**.
- Đánh giá reader trên crop thật và số chữ số thật được ghi riêng, không nhầm với tự định vị toàn ảnh.
- Holdout toàn luồng chạy từ ảnh nguyên, không đưa vùng/nhãn/số chữ số thật vào inference: ghi IoU mặt công tơ/vùng số, exact-match, coverage, CER, lỗi khi trả lời, p50/p95.
- Score chưa hiệu chuẩn; thống kê lỗi score cao và cận trên Wilson 95% không tự biến score thành xác suất. Ví dụ không có lỗi trong 30 ảnh vẫn chưa chứng minh sai số thực dưới 1%.

Artifact ban đầu luôn TESTING, kèm run_id, hash dataset và danh sách artifact/checksum thuộc phiên hoàn tất. Lỗi/timeout reader làm kiểm định toàn quy trình không hoàn tất; không bịa điểm. Snapshot đầy đủ không trả về UI mỗi lần polling, tránh payload lớn.

## 5. Kích hoạt có kiểm soát

Server kiểm tra file/checksum, loại hỗ trợ, provenance từ phiên COMPLETED và nhãn/nhóm holdout hiện tại còn khớp snapshot. Metrics JSON tự nhập khi đăng ký thủ công không thay thế phiên train thật.

Gate hiện hành (điều kiện kỹ thuật tối thiểu, không phải chứng nhận sản xuất):

- Validation tách nhóm đã xác minh, ít nhất 30 ảnh.
- Holdout độc lập được xác minh, ít nhất 30 ảnh, kiểm định toàn quy trình hoàn tất.
- Bộ định vị: điểm sai số tọa độ validation ≥0,8 và IoU vùng tương ứng trên holdout toàn luồng ≥0,8.
- Bộ đọc: exact-match và coverage trên crop holdout ≥95%; trên toàn luồng ≥90%.
- Kích hoạt theo thứ tự **định vị công tơ → vùng số → bộ đọc**, cùng phiên bản. Đổi bộ định vị sẽ lưu trữ bộ đọc khác phiên để tránh trộn pipeline chưa đánh giá.

Mô hình cũ không đạt gate giữ lịch sử, không được tự dùng lại. Mọi kích hoạt có audit; worker nạp ứng viên đã xác minh ở job tiếp theo. **Tự xác nhận kết quả vẫn khóa**, kể cả khi đã kích hoạt bộ đọc.

## 6. Tài nguyên và kiểm thử

Compose ≥2.22 dùng named build context để trainer kế thừa môi trường PARSeq. Mặc định trainer CPU 1 core/2 GiB, ngân sách vòng học 7.200 giây. Trainer/reader dùng NumPy 1.x tương thích Torch CPU đã pin; worker dùng NumPy 2.x ở image riêng. Không đổi NumPy chung khiến Torch mất cầu nối ảnh. Chỉ chạy một replica trainer; hệ thống chưa có distributed training/HA.

Smoke test ngoại tuyến, chỉ ảnh tổng hợp, không database/volume thật:

```text
docker compose --env-file .env.example build reader-parseq trainer
docker run --rm --network none --read-only --tmpfs /tmp:size=256m,mode=1777 --cap-drop ALL --security-opt no-new-privileges:true elec_man-trainer python -m ai.tools.smoke_sequence_training
```

Lệnh kiểm chứng optimizer đổi decoder, encoder không đổi, safetensors nạp lại/inference giống nhau, checksum sai bị từ chối và reset pretrained đúng. Không dùng kết quả trên ảnh tổng hợp để tuyên bố độ chính xác công tơ thật.

37 nhãn trong snapshot công khai vẫn được giữ nguyên. Chưa xác minh danh tính/nhóm nên chưa tự coi là dữ liệu đủ để kích hoạt. Cần bạn xác minh trong UI và bổ sung ảnh độc lập, ảnh mờ/phản chiếu/chuyển số/công tơ khác; chưa có cam kết chỉ thêm ảnh là hoàn thành AI sản xuất.

Tham khảo triển khai từ [PARSeq chính thức](https://github.com/baudm/parseq), định dạng [safetensors](https://huggingface.co/docs/safetensors/main/en/api/torch) và bộ đối chứng [PaddleOCR 3.7.0](https://github.com/PaddlePaddle/PaddleOCR/releases/tag/v3.7.0). Xem [pipeline](ai-pipeline.md), [độ tin cậy](ai-reliability.md), [giám sát/sao lưu](operations-monitoring.md).
