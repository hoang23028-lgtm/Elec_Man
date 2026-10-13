# Pipeline huấn luyện và vận hành — 13/10/2026

## Thay đổi đã kiểm chứng

Migration `20261013_0029` thêm dataset_annotations, không sửa số/vùng ảnh thật. Có UI xác minh nhóm/nhãn/phân tập, khóa holdout, kiểm tra revision, audit trước–sau; snapshot bất biến theo phiên. Thay việc chia dataset tự động cũ bằng một chính sách chung cho API/trainer/công cụ benchmark.

Định vị vùng số học trong mặt công tơ chỉnh phối cảnh, ánh xạ bốn góc về ảnh gốc. Có chương trình học decoder/head PARSeq-tiny với encoder cố định, chọn epoch bằng validation, lưu safetensors. PP-OCR/pretrained PARSeq làm đối chứng; đánh giá holdout crop và toàn ảnh được phân biệt. Kiểm tra nguồn phiên/artifact và nhãn hiện tại khi kích hoạt, buộc cùng phiên bản bộ định vị/bộ đọc. Tự xác nhận vẫn khóa.

Thêm hủy phiên, giới hạn trainer 1 CPU/2 GiB/ngân sách học, bỏ OCR cảnh khi bộ định vị học đã trả vùng hợp lệ, đóng client khi đổi model, không trả snapshot nặng khi polling. Worker/trainer tách NumPy ABI để môi trường Torch CPU thực sự chạy được.

Giám sát hàng đợi/lỗi/p50/p95/dung lượng/backup chỉ cho SUPER_ADMIN. Backup quản lý có khóa OS, tạm dừng writer, verify/checksum/kiểm tra đường dẫn, finally bật lại writer; watch và retention có lựa chọn rõ ràng, không tự xóa backup thật.

## Kiểm thử phần mềm

- Backend: 850 test đạt, bao gồm snapshot seed theo lô và chính sách nhóm/holdout/activation/backup lock/retention/failure recovery.
- PostgreSQL disposable: 32 test đạt, bao gồm seed snapshot gốc dưới migration mới, chỉnh annotation/revision/holdout/audit/phân quyền và tranh chấp train/kích hoạt.
- AI ở Docker: 38 test đạt. Hàm chia tập cũ được bỏ; kiểm thử chống rò rỉ nhóm hiện nằm trong policy backend dùng chung.
- Frontend: 18 test đạt; TypeScript, ESLint và production build đạt.
- Ruff, docs links, scanner secret có độ tin cậy cao, manifest snapshot và Compose config đạt. Scanner không phải cam kết tuyệt đối không có bí mật hoặc lỗ hổng.

Smoke PARSeq thật, network none/read-only/tmpfs/cap_drop ALL/UID10001, ảnh tổng hợp: optimizer thay decoder, encoder không đổi, safetensors reload/inference bằng nhau, checksum sai bị từ chối, reset pretrained khớp. Loss lần chạy một epoch 0,2845459; **không** là điểm chính xác ảnh thực.

## Tải hỗn hợp có giới hạn

Sandbox riêng với 15 ảnh/khách hàng giả, không volume/DB thật. OCR được tiêm tại ranh giới worker, không đo OCR thực. Song song CPU optimizer 20 epoch trên 2 crop giả; 19 epoch hoàn tất trong cửa sổ HTTP 8,585 giây.

| Phép thử | Số yêu cầu | p50 | p95 | Lỗi |
|---|---:|---:|---:|---:|
| Upload 5 luồng | 5 | 471,92 ms | 573,21 ms | 0 |
| Đọc 10 luồng | 120 | 189,70 ms | 720,49 ms | 0 |

Phân quyền/CSRF/cookie/session/login limiter/CORS đạt. HTTPS probe riêng dùng chứng chỉ thử đã tin cậy trong client: redirect 308, HSTS, cookie Secure/HttpOnly/SameSite, OpenAPI ẩn và giới hạn login đạt. Số liệu một máy/một lần, không so sánh để tuyên bố nhanh nhất hoặc bảo đảm SLA production.

## Sao lưu, phục hồi và local

Backup verified `backups/20261013T153416Z-38959f6b`: SQL, kho ảnh và kho model. Diễn tập ở database/thư mục tạm phục hồi 660 khách hàng, 61 ảnh, 37 nhãn, 0 chỉ số tháng; 134 tệp kho ảnh (133 tệp nghiệp vụ và trạng thái maintenance) + 3 tệp model khớp hash. Tài nguyên diễn tập đã dọn, không gắn volume production.

Backup trước cập nhật `backups/20261013T155556Z-422c3797` cũng verified. Đã áp dụng migration mới và recreate localhost bằng cấu hình gốc trong bộ nhớ, không tạo `.env` hoặc đổi secret/mật khẩu. Trang chủ/API ready HTTP 200; sau cập nhật vẫn 660 khách hàng, 61 ảnh, 37 LABELED, 0 annotation xác minh, 0 model ACTIVE, 1 phiên train lịch sử. Không thêm/chỉnh nhãn thật, không huấn luyện hoặc kích hoạt model thật trong lần này. Snapshot công khai ban đầu không thay đổi.

UI đã kiểm tra bằng tài khoản giả trong sandbox: lưu nhóm/phân tập phản ánh vào bảng, phân trang có tổng trang, trạng thái/điều kiện train, form giữ dữ liệu, mục giám sát và cảnh báo. Thiết kế theo hệ token sẵn có/ui-ux-pro-max; kiểm tra viewport hẹp. Sandbox hết thời hạn gây lỗi mạng được phát hiện, thông báo fetch đã đổi sang tiếng Việt; đó không phải lỗi localhost production.

Sau khi chủ dự án đăng nhập lại, đã kiểm tra chỉ đọc trên localhost bằng SUPER_ADMIN: 61 ảnh / 6 trang, 37 nhãn chưa xác minh nhóm; ảnh xem trước tải đúng, không tràn trang ở breakpoint 1200px (bảng cuộn ngang trong vùng riêng). Huấn luyện tiêu chuẩn bị vô hiệu ở 0/200 mẫu học; mô hình cũ bị khóa đúng lý do; Giám sát hiển thị hàng đợi/lỗi bằng 0, bản backup đã kiểm tra checksum và độ trễ từ 61 tác vụ lịch sử. Sửa thêm trạng thái Giám sát sang tiếng Việt và dùng chung hàm hiển thị với màn hình Huấn luyện. Không lưu form xác minh hoặc thay dữ liệu thật trong QA.

## Việc cần quyết định/dữ liệu bổ sung

37 mẫu chưa xác minh nhóm; không thể tự đoán để chứng nhận test độc lập. Chủ dữ liệu kiểm tra nhóm/nhãn, phân tập và thu thập holdout mới trước train tiêu chuẩn. Chưa có mô hình chuyên biệt được chứng minh đạt gate trên dữ liệu thực; chưa triển khai Internet.

Watch/retention đã có trong phần mềm, nhưng chưa tự cài tác vụ toàn máy hoặc chọn kho backup ngoài máy. Cần chọn giờ bảo trì, supervisor/Task Scheduler, nơi nhận dữ liệu riêng và mã hóa trước production. Xem [hướng dẫn train](../training.md) và [vận hành](../operations-monitoring.md).

## Phát hành GitHub và kiểm thử tự động

Source đã push lên `master`, commit `0ed8516be4b211cdf8f22efd379e2cbbb85ce41a`. [Kiểm thử và build](https://github.com/hoang23028-lgtm/Elec_Man/actions/runs/38428669673) hoàn tất thành công: backend, integration PostgreSQL, frontend, AI, Compose, secret/docs policy và smoke optimizer PARSeq offline. [CodeQL Python/TypeScript](https://github.com/hoang23028-lgtm/Elec_Man/actions/runs/38428669410) cũng hoàn tất thành công. Đây là kết quả của đúng source mới, không dùng workflow của commit trước làm bằng chứng.

Tổng 938 test local (850 backend + 32 integration + 38 AI + 18 frontend), cộng smoke optimizer thật. CI và scanner đạt không chứng minh tuyệt đối an toàn, độ chính xác ảnh thực hoặc SLA production. Báo cáo này mô tả commit source nêu trên; commit tài liệu bổ sung sau đó không thay thuật toán hoặc dữ liệu.
