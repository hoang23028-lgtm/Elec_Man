# Kế hoạch cải tiến đang thực hiện

Ngày bắt đầu: 13/10/2026. Yêu cầu: thực hiện toàn bộ các bước đề xuất, không tự thay nhãn thật, không kích hoạt mô hình hoặc mở tự xác nhận khi chưa có kiểm định.

1. Đã triển khai/kiểm thử seed theo lô, không ghi đè, tệp tạm; phục hồi snapshot cũ an toàn dưới migration mới.
2. Đã thêm UI/API xác minh nhóm/nhãn/phân tập, khóa holdout, snapshot bất biến. **Chờ người dùng xác minh 37 nhãn thật**, không tự gán nhóm.
3. Đã học vùng số trong mặt công tơ chỉnh phối cảnh, đo IoU/crop và toàn luồng. Chưa có bằng chứng model mới chính xác trên thực địa.
4. Đã tích hợp fine-tune PARSeq-tiny/safetensors, giữ PP-OCR đối chứng; optimizer/reload/checksum/reset thực sự đạt smoke test trên ảnh giả.
5. Đã thêm gate holdout/provenance/checksum/nhãn hiện tại/cùng phiên bản; tự xác nhận vẫn khóa. Chờ đủ dữ liệu độc lập và kết quả đạt gate.
6. Đã có giám sát, tải hỗn hợp, backup có khóa/verify/watch/retention opt-in, diễn tập phục hồi. **Chờ lựa chọn lịch/supervisor và nơi backup ngoài máy**, chưa tự thay cấu hình toàn máy.
7. Đã đồng bộ UI, kiểm thử local, migration/backup/cập nhật localhost và tài liệu; source đã phát hành lên `master` tại commit `0ed8516`. Cả workflow kiểm thử/build và CodeQL của commit này đều đạt; xem liên kết bằng chứng trong báo cáo.

Phần người dùng cần làm sau khi có công cụ: xác minh định danh và nhãn của ảnh thật, phân holdout trước huấn luyện, bổ sung ảnh đa dạng. Không tự coi 37 mẫu là đủ sản xuất hoặc bịa tỷ lệ chính xác.

Xem [báo cáo kiểm chứng](reports/training-pipeline-upgrade-2026-10-13.md), [hướng dẫn train](training.md) và [vận hành/backup](operations-monitoring.md).

## Bổ sung bản 4–5, ngày 21/10/2026

Đã hoàn tất kiểm thử local đối chứng MobileNetV3/Ridge và đo OCR/encoder ONNX: 969 test, hai smoke offline và browser sandbox. Mặc định encoder Torch, mô hình mới TESTING; chưa có holdout độc lập nên không kích hoạt. Xem [báo cáo và giới hạn](reports/locator-latency-release-2026-10-21.md).

Đã giảm fallback OCR khách hàng và chạy song song phần độc lập; v2 định vị vùng số có tăng cường crop, chọn epoch theo IoU. 990 test đạt; IoU vùng số validation 39,4% → 58,2%, latency chẩn đoán 11,8 → 4,3 giây trên 5 ảnh. Không thay bằng chứng holdout bằng điểm validation; 0 ACTIVE, tự xác nhận vẫn khóa. Xem [báo cáo tối ưu và các giới hạn](reports/ocr-localization-optimization-2026-10-21.md).
