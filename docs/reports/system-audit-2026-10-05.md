# Rà soát hệ thống — 05/10/2026

> Báo cáo lịch sử theo ngày, không phải hướng dẫn bản hiện hành. Xem [danh mục tài liệu](../README.md).

## Cập nhật khắc phục cùng ngày

Bốn phát hiện dưới đây đã được sửa sau khi người dùng yêu cầu triển khai:

- Train tự động dừng sau phiên FAILED; quản trị phải chạy thủ công thành công mới khôi phục tự động. Không tự thử lại vô hạn, kể cả khi dữ liệu vẫn đủ ngưỡng.
- Mọi producer đi qua PostgreSQL advisory transaction lock chung trước khi kiểm tra và tạo phiên; điều kiện tự động được kiểm tra lại bên trong khóa.
- Ngưỡng kỹ thuật tối thiểu thống nhất là 3; cấu hình cũ thấp hơn được chặn ở chính sách runtime, API mới từ chối giá trị dưới 3 và input UI đặt min=3.
- Cấu hình upload/retry/chu kỳ worker chuyển thành chỉ đọc, API trả giá trị môi trường backend thay vì giá trị database không có hiệu lực. UI không gửi các trường đó khi lưu; API chặn sửa trực tiếp. Môi trường worker cần được đồng bộ khi triển khai và không được mô tả như số đo trực tiếp từ worker.

Các phát hiện gốc bên dưới được giữ để truy vết. Các giới hạn về benchmark thực tế, E2E, HTTPS, biểu giá và diễn tập khôi phục backup vẫn còn; không được hiểu là đã hoàn thành chỉ nhờ sửa bốn lỗi này.

Đã triển khai lại localhost sau backup `backups/audit-20261005-203734/database.dump`. Kiểm tra hai session PostgreSQL thật xác nhận session thứ hai không lấy được khóa trong khi session thứ nhất giữ khóa, và lấy được sau rollback; không tạo phiên train hoặc thay đổi dữ liệu trong kiểm tra này. Đây là kiểm tra cơ chế khóa, không phải stress test toàn pipeline.

## Kết luận đợt rà soát ban đầu

Hệ thống chạy được tại localhost, nhưng chưa thể kết luận đã kiểm chứng toàn bộ luồng thực tế hoặc sẵn sàng triển khai diện rộng. Đợt rà soát ban đầu chỉ kiểm tra; phần sửa sau đó được mô tả ở mục cập nhật phía trên.

## Phát hiện cần xử lý

### P1 — Huấn luyện tự động thử lại không giới hạn sau lỗi

- `backend/app/services/training_service.py`: `dataset_summary` chỉ lấy số mẫu của phiên COMPLETED; `maybe_enqueue_auto` chỉ chặn PENDING/RUNNING, không chặn dataset vừa FAILED.
- `ai/trainer.py`: khi lỗi, phiên được đánh dấu FAILED và vòng lặp tiếp tục sau 5 giây.
- Khi vẫn đủ mẫu mới, cùng dữ liệu và cùng lỗi có thể tạo thêm phiên liên tiếp, tốn tài nguyên và tăng log/database. Đây là suy luận từ vòng lặp đã kiểm tra; kiểm tra mock đã xác nhận hai lần gọi với cùng dataset và không có phiên hoạt động đều enqueue.
- Đề xuất: nhận diện phiên bản dataset, backoff và giới hạn thử lại; lỗi cố định phải chờ sửa dữ liệu/cấu hình hoặc thao tác thủ công.

### P2 — Kiểm tra phiên train đang hoạt động chưa nguyên tử

- `enqueue_training` SELECT phiên đang chạy rồi INSERT, không khóa điều phối; bảng training_runs không có ràng buộc chỉ một phiên hoạt động.
- Hai request thủ công đồng thời hoặc request thủ công trùng thời điểm trainer tự lên lịch có thể cùng vượt kiểm tra. Chưa chạy thử cạnh tranh trên database thật.
- Đề xuất: khóa transaction chung hoặc ràng buộc database và xử lý xung đột trả 409.

### P2 — Ngưỡng 2 mẫu báo sẵn sàng nhưng không train được

- `settings_service.py` chấp nhận `training_min_samples=2`.
- `dataset_summary` đánh dấu ready khi eligible >= minimum.
- `enqueue_training` từ chối nếu eligible < 3.
- Đã tái hiện độc lập: cấu hình 2 được chấp nhận, ready=True với 2 mẫu, enqueue trả 422.
- Đề xuất: dùng cùng một ngưỡng tối thiểu 3 ở schema, chính sách, API và UI; vẫn giữ ngưỡng chất lượng mặc định cao hơn.

### P2 — Một số cấu hình UI không được tiến trình sử dụng

- UI mô tả chu kỳ worker được áp dụng sau khởi động lại, nhưng `ai/worker.py` đọc `get_settings().worker_poll_interval_seconds` từ môi trường, không đọc bảng system_settings.
- Tương tự giới hạn upload: UI lưu `max_upload_size_mb`, còn `storage_service.py` dùng `max_image_size_mb` từ môi trường.
- Không tìm thấy cầu nối từ giá trị database sang môi trường trong luồng đã rà soát. Khởi động lại riêng dịch vụ không đủ để áp dụng giá trị UI.
- Đề xuất: phân biệt cấu hình động và cấu hình triển khai chỉ đọc, hiển thị giá trị thực tế đang có hiệu lực.

## Phạm vi và bằng chứng

| Nhóm | Đã kiểm tra | Giới hạn |
|---|---|---|
| Đăng nhập/đăng ký/phiên | Bộ test auth, CSRF, rate limit, session restore và đăng ký | Chưa E2E trên phiên quản trị của người dùng |
| Phân quyền | Ma trận SUPER_ADMIN/ADMIN/VIEWER và gọi API thiếu quyền | Không tạo tài khoản thật để thử |
| Upload/kho ảnh | Test chữ ký ảnh, loại file, giới hạn, đường dẫn; đọc luồng ghi file | Chưa stress test upload đồng thời hoặc đầy ổ đĩa |
| OCR/khoanh vùng | 30 test AI và test region recognition | Không phải benchmark độ chính xác trên tập ảnh thực độc lập |
| Nhãn/xác nhận/từ chối | Test review, khôi phục, snapshot tháng, rollback file | Chưa kiểm tra UI quản trị trực tiếp trong phiên hiện tại |
| Khách hàng/báo cáo | Test import, đối chiếu, export và phân trang | Không xuất báo cáo thật để tránh tạo dữ liệu/audit ngoài nhu cầu |
| Dashboard/tính tiền | Test SQL đối chiếu hàm Python, kỳ thiếu/thay đổi năm; dashboard công khai | Biểu giá chưa version theo ngày; đây không phải chứng nhận hóa đơn hợp lệ pháp lý |
| Huấn luyện/mô hình | Test pipeline/policy và đọc luồng trainer; phát hiện ở trên | Chưa train lại, kích hoạt hay đổi mô hình thật |
| Cấu hình/nhật ký | Đọc luồng settings, user audit, review before/after | Chưa kiểm tra khôi phục backup đầy đủ và cảnh báo lỗi đầu cuối |
| Triển khai | Các container đang chạy, dịch vụ có healthcheck báo healthy; readiness HTTP 200 | Local HTTP, chưa thử HTTPS trên hạ tầng Internet |

## Kiểm thử trong đợt này

- Backend: 279 passed, 2 cảnh báo deprecation dependency.
- AI: 30 passed trong container tạm với cấu hình SQLite test, không nối database thật.
- Frontend: typecheck và lint đạt; 9 test đạt.
- Ruff backend/AI: đạt.
- `npm audit --omit=dev`: 0 lỗ hổng được báo cáo. Không đồng nghĩa toàn bộ hệ thống không có lỗ hổng; lần audit đầy đủ trước đó còn cảnh báo nhóm công cụ phát triển.
- Database và dịch vụ không bị thay đổi trong đợt rà soát này.

## Cần kiểm tra tiếp

1. Đã sửa bốn phát hiện huấn luyện/cấu hình và bổ sung 11 regression test; tổng backend đạt 290, frontend 9; lint/typecheck đạt.
2. Kiểm tra UI với phiên SUPER_ADMIN, ADMIN và VIEWER thật trong môi trường test; thao tác có ghi dữ liệu cần dùng dữ liệu thử riêng.
3. Benchmark OCR bằng tập kiểm định độc lập; không suy ra độ chính xác từ việc unit test đạt.
4. Kiểm thử concurrent upload/confirm/train và khôi phục backup trong database riêng.
5. Tách đợt kiểm tra biểu giá theo thời điểm hiệu lực, và kiểm tra HTTPS/cookie trên môi trường triển khai thực tế.
