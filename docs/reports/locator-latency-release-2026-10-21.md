# Kiểm chứng bản 4–5: định vị và tốc độ OCR

Chốt kiểm thử ngày 21/10/2026. Các phép đo ảnh thật ngày 14/10 bên dưới là chẩn đoán trên dữ liệu phát triển, không phải holdout độc lập và không chứng minh sẵn sàng tự động hóa.

## Thay đổi

- Huấn luyện/so sánh cặp MobileNetV3-small với Ridge trên cùng snapshot; xuất ONNX, kiểm tra tương đương số học. Backbone cố định, chỉ học đầu bốn góc; một công tơ trên ảnh.
- UI chọn đối chứng, xem IoU và thời gian; gate cùng phiên/kiến trúc, holdout/provenance/checksum/nhãn hiện tại. Không tự kích hoạt.
- PARSeq có lựa chọn encoder ONNX FP32; decoder Torch vẫn giữ nguyên. Mặc định Torch vì p95 ONNX chưa tốt hơn.
- Timing từng bước, tách tự động/vùng thủ công, allowlist dữ liệu giám sát. Ridge dùng hệ phương trình nhỏ hơn theo số mẫu/đặc trưng.
- Cache pretrained nằm trong image, hoạt động offline dù Compose đặt XDG cache trong tmpfs. NumPy 1.26 tương thích Torch đã pin.
- Công cụ benchmark đọc nhãn và ảnh, không sửa DB; báo cáo mới, giới hạn dung lượng và đường dẫn, không ghi đè. Báo cáo riêng/backup không được đưa vào Git.

## Phép đo ảnh đã gắn nhãn ngày 14/10

37 ảnh duy nhất: 31 train, 6 validation, 0 holdout; danh tính công tơ chưa được xác minh. Phiên chẩn đoán hoàn tất sau khi sửa lỗi cache TorchVision của lần thử đầu. Bốn artifact mới ở TESTING, không thay mô hình ACTIVE.

| Định vị tự động trên 6 ảnh validation | IoU công tơ | IoU vùng số | p95 định vị |
|---|---:|---:|---:|
| Ridge | 66,4% | 26,1% | 4,59 ms |
| MobileNetV3 | 79,1% | 39,4% | 7,33 ms |

IoU không phải tỷ lệ đọc đúng chỉ số. Vùng số vẫn chưa đạt chất lượng yêu cầu. Chưa có kiểm định độc lập, không kích hoạt.

| Đọc vùng người dùng lưu, biết số chữ số | p50 | p95 | Đúng chuỗi / lần đo warm |
|---|---:|---:|---:|
| PARSeq encoder Torch | 107,61 ms | 271,11 ms | 50/74 |
| PARSeq encoder ONNX | 99,14 ms | 303,06 ms | 50/74 |

37 ảnh × 3 vòng × 2 runtime; bỏ vòng đầu khỏi summary warm. Chuỗi hai runtime giống nhau trên mọi lần đo; không có lỗi dịch vụ. Không gọi 74 lần lặp là 74 ảnh độc lập. ONNX giảm median nhưng tăng p95, nên không đổi mặc định.

Phép đo tự động toàn ảnh ngày 14/10: 5 ảnh × 3 vòng, bỏ vòng đầu; p50 4.748 ms, p95 7.904 ms, 0/10 lần warm đúng chuỗi, không lỗi dịch vụ. Median OCR khách hàng 3.149 ms, OCR cảnh 1.068 ms, đọc số 76,54 ms. Đây là mẫu nhỏ, không suy rộng accuracy toàn hệ thống. Báo cáo tmpfs lần này đã mất khi container khởi động lại; không giả vờ có tệp gốc còn lưu. Báo cáo vùng thủ công vẫn được giữ riêng trong thư mục ignored.

## Phạm vi kiểm chứng

Kiểm tra lại source ngày 21/10: **870 backend + 33 PostgreSQL riêng + 47 AI image vừa build + 19 frontend = 969 test đạt**. Frontend typecheck/lint/production build đạt; Ruff/check format, secret policy, liên kết tài liệu và snapshot công khai đạt. Hai smoke offline thực sự chạy optimizer và xuất/đọc ONNX đạt. Hai warning deprecation backend được giữ nguyên, không che lỗi. Test giới hạn báo cáo ban đầu bị lỗi tên tham số pytest quá dài trên Windows; đã đặt ID ngắn và chạy lại toàn bộ backend đạt.

Browser: môi trường sandbox ngẫu nhiên, tài khoản và ảnh giả, không dùng DB/volume thật. Đã kiểm tra lựa chọn MobileNetV3/epoch, nút huấn luyện khóa khi thiếu dữ liệu, bảng đối chứng có số liệu giả và holdout “Chưa đo”, nút kích hoạt khóa có lý do, giám sát tách vùng thủ công/tự động khi thiếu timing. Kiểm tra 375 px và 1280 px không tràn chiều ngang toàn trang (bảng cuộn riêng); không có console error. Không gọi đây là kiểm thử tương tác train trên dữ liệu thật. Bằng chứng ảnh lưu riêng trong thư mục ignored.

Đo lại 5 ảnh/3 vòng khi máy đồng thời chạy build/test ngày 21/10: p50 16.691 ms, p95 21.966 ms; OCR khách hàng chạm ngân sách 8 giây ở median. Không so tốc độ này với phép đo nhàn rỗi ngày 14/10 để kết luận hồi quy; cần phép đo trước/sau cùng điều kiện. CI/CodeQL phải gắn commit mới trên GitHub, không sử dụng kết quả của commit cũ.

Không thay nhãn thật, mã khách hàng, chỉ số tháng, phân tập hoặc kích hoạt mô hình. Không tái xuất snapshot công khai hay đưa báo cáo/backup riêng lên GitHub.
