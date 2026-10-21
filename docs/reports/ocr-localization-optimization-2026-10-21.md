# Tối ưu OCR khách hàng và vùng số — 21/10/2026

Thực hiện sau khi [bản 4–5](locator-latency-release-2026-10-21.md) đã được đẩy lên GitHub và CI/CodeQL đạt. Không tuyên bố hoàn thành độ chính xác AI sản xuất từ ít ảnh phát triển.

## Thay đổi đã áp dụng

- Tái sử dụng dòng OCR để tìm PN2.001/PN.001/UB.001; xử lý dấu tiếng Việt và khoảng trắng quanh dấu chấm. Không đoán lại mã, không hạ PN2 thành PN. Mã mâu thuẫn thì từ chối đề xuất; server vẫn đối chiếu master trước xác nhận.
- Tesseract giảm từ sáu lượt/ngân sách 8 giây xuống tối đa bốn lượt/ngân sách 3 giây. Hết ngân sách cần người kiểm tra. Khi đã bỏ OCR cảnh do định vị học hợp lệ, OCR riêng crop khách hàng.
- Nhánh mã khách hàng chạy song song với hai dịch vụ đọc số. Không dùng session DB trong thread. Job vẫn đợi đủ hai nhánh; chưa có streaming kết quả sớm. `customer_wait` ghi thời gian chờ còn lại, không cộng chồng các timing.
- Giới hạn pool ORT của RapidOCR một thread để tránh tranh CPU.
- MobileNetV3 v2: 320 px, đặc trưng không gian 5×5, loss theo kích thước vùng, chọn epoch theo IoU validation. Học vùng số bằng crop công tơ dự đoán, crop chuẩn và hai nhiễu nhỏ trong train; validation không được cho vùng công tơ thật.
- Model v1 vẫn đọc đúng contract 192 px. IoU trên từng artifact mới khớp benchmark của kiến trúc tương ứng, không dùng nhầm số Ridge.

Chi tiết cách chạy và giới hạn ở [định vị và tốc độ](../locator-and-latency.md).

## Kết quả định vị

Giữ nguyên snapshot SHA `2273811446f110a9e8463a506053779704a285e423341e5b6ff9d33d3aeecc85`: 37 ảnh duy nhất, 31 train, 6 validation, **0 holdout**; chưa xác minh nhóm công tơ. 124 crop tăng cường của vùng số chỉ phát sinh từ 31 ảnh train, không phải 124 ảnh độc lập.

| Ứng viên | IoU công tơ | IoU vùng số tự động |
|---|---:|---:|
| Ridge | 66,4% | 26,1% |
| MobileNetV3 v1 ngày 14/10 | 79,1% | 39,4% |
| V2 chỉ tăng độ phân giải/loss, chưa chống lệch crop | 78,5% | 39,0% |
| V2 có crop dự đoán/nhiễu train và validation theo crop dự đoán | 78,5% | **58,2%** |

Lần thử chỉ tăng độ phân giải không cải thiện vùng số; không giấu kết quả đó. Cải thiện chính đến từ xử lý lệch điều kiện crop giữa train và inference. IoU công tơ v2 hơi thấp hơn v1. Không gọi IoU là accuracy đọc chỉ số.

Phiên cuối `506f1324-eb2b-46b0-ace6-dcb080344f89`: 40 epoch, hoàn tất trong khoảng 31,6 giây ở máy thử; chọn epoch công tơ 23/vùng số 17. p50/p95 định vị cặp v2 trên 6 ảnh: 18,04/21,14 ms, Ridge 5,82/7,76 ms. Bốn artifact mới TESTING, tổng 15 artifact TESTING, **0 ACTIVE**. Chưa đủ holdout độc lập/IoU gate, không kích hoạt hoặc mở tự xác nhận.

Đây là validation được dùng chọn trọng số và cải tiến thuật toán, không là phép thử độc lập. Cần tập công tơ/khách hàng mới, xác minh nhóm và giữ holdout riêng trước khi đánh giá khả năng triển khai.

## Kết quả hiệu năng

Benchmark tự động cùng 5 hash ảnh đã gắn nhãn, 3 vòng, loại vòng đầu; mỗi summary có 10 lượt warm, không phải 10 ảnh độc lập. Hai lần chạy trước/sau trên cùng máy nhưng không phải thử nghiệm A/B ngẫu nhiên; tải Windows/Docker có biến động, không xem là SLA hay cam kết phần trăm tăng tốc.

| Phép đo | p50 toàn pipeline | p95 toàn pipeline | OCR khách hàng p50 |
|---|---:|---:|---:|
| Trước tối ưu, lượt ít tải hơn sau build đầu | 11.792 ms | 18.238 ms | 7.693 ms |
| Sau tối ưu, lượt cuối không train/build đồng thời | **4.263 ms** | **4.755 ms** | **2.905 ms** |

Sau tối ưu: OCR cảnh p50 1.492 ms, đọc số 858 ms, phần chờ khách hàng sau đọc số 1.873 ms. Không cộng các nhánh song song thành tổng. Không lỗi dịch vụ, DB không bị benchmark sửa.

**Cả trước và sau đều 0/10 lượt warm đọc đúng chuỗi trên 5 ảnh tự động này**, vì chưa có bộ định vị ACTIVE. Tăng tốc không đồng nghĩa sửa xong accuracy. Hai lượt sau trích được đề xuất mã khách hàng; năm lượt hết ngân sách fallback. Chưa có đủ mã khách hàng chuẩn trên ảnh để đánh giá accuracy mã: `customer_accuracy_evaluated=false`. Không tính “tìm được mã” thành “mã đúng”.

Báo cáo JSON đầy đủ lưu riêng trong thư mục ignored, không xuất bản dữ liệu mới. Số latency của benchmark không tự xuất hiện trong Giám sát vì không tạo AI result/job mới.

## Kiểm chứng và triển khai

- 871 backend unit, 33 PostgreSQL integration riêng, 67 AI test trong image vừa build, 19 frontend: **990 test đạt**.
- TypeScript, ESLint, frontend production build, Ruff/check format, secret policy, liên kết tài liệu và snapshot công khai đạt.
- Hai smoke offline: optimizer/reload/checksum/reset PARSeq; v2 train/export/ONNX, v1 contract thực sự, encoder parity và từ chối encoder hash không khớp.
- Browser sandbox mới bằng image frontend hiện tại: lựa chọn v2/epoch hiện đúng, trạng thái khóa khi thiếu dữ liệu, giám sát giải thích thời gian song song, không console error. Không nhập mật khẩu thật hoặc thử thay nhãn thật. Skill UI/UX giữ bảng trong khung cuộn riêng và dùng mô tả rõ ràng về điều kiện chưa được kích hoạt.
- Localhost cập nhật với env gốc giữ trong bộ nhớ, không tạo lại `.env`. Sao lưu trước mỗi cập nhật đã verify checksum; nguồn ảnh/nhãn/khách hàng/chỉ số tháng không bị thay đổi. 660 khách hàng, 61 ảnh, 37 LABELED/24 REJECTED, 0 chỉ số tháng, 0 nhóm đã xác minh giữ nguyên.
- Không tái xuất snapshot public, không đẩy backup SQL, báo cáo riêng, ảnh hoặc model mới lên GitHub. CI/CodeQL của commit tối ưu phải kiểm tra riêng trên GitHub.

Phần còn cần dữ liệu: xác minh 37 nhãn/nhóm, bổ sung ảnh đa dạng và holdout độc lập, kiểm định full-chain/đúng chuỗi/mã khách hàng, hiệu chuẩn score. Chưa thể tuyên bố nhận diện tự động đạt yêu cầu sản xuất.
