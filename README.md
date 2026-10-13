# Hệ thống AI quản lý đồng hồ điện

Ứng dụng tiếng Việt xử lý ảnh công tơ theo lô, gắn nhãn/kiểm duyệt, đối chiếu khách hàng, lưu chỉ số từng tháng và xuất JSON/Excel. Bản chia sẻ chuẩn ở nhánh **master** của [Elec_Man](https://github.com/hoang23028-lgtm/Elec_Man).

## Chạy ngay trên máy mới

Cài Git và Docker (Linux containers + Compose), mở Docker, rồi:

```text
git clone https://github.com/hoang23028-lgtm/Elec_Man.git
cd Elec_Man
```

Windows:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start.ps1
```

Linux/macOS:

```bash
bash scripts/start.sh
```

Bộ cài tự tạo cấu hình riêng bằng secret ngẫu nhiên, build các dịch vụ/trọng số, áp dụng migration và chờ readiness. Lần đầu nhập mật khẩu 12–256 ký tự cho tài khoản **admin**; không có mật khẩu mặc định. Mở [http://localhost/](http://localhost/).

Lần build đầu cần Internet và có thể lâu vì tải hai bộ đọc AI. Không cần cài Python/Node/PostgreSQL trên host để dùng Docker. [Hướng dẫn cài chi tiết](docs/installation.md) có đổi cổng, chọn tên quản trị và xử lý 502/build/login.

## Sử dụng

1. Quản trị → nhập khách hàng JSON hoặc thêm thủ công. Có [mẫu dữ liệu giả](examples/customers.json).
2. Vận hành → tải ảnh → kiểm tra/khoanh vùng → lưu nhãn hoặc xác nhận mã, chỉ số nguyên và tháng.
3. Quản trị → chỉ số tháng → tải báo cáo JSON/Excel; Tổng quan hiển thị thống kê/tiền tạm tính.

Guest/VIEWER chỉ xem Tổng quan. ADMIN làm nghiệp vụ. SUPER_ADMIN quản lý thêm tài khoản, huấn luyện, cấu hình và truy vết. [Hướng dẫn sử dụng](docs/usage.md) · [Ma trận quyền](docs/roles.md).

## AI và dữ liệu: điều gì có sẵn?

- Bộ đọc toàn chuỗi **PP-OCRv6 small + PARSeq-tiny** trong hai dịch vụ nội bộ; không mock, không gửi ảnh lên cloud.
- Tiền xử lý/crop OpenCV, OCR mã khách hàng, đối chiếu database; khoanh bốn góc và lưu nhãn thủ công.
- Trainer học **hai bộ định vị Ridge** và **fine-tune PARSeq-tiny** từ nhãn được kiểm tra. Phân nhóm công tơ, khóa holdout, đối chứng reader và kiểm định toàn quy trình trước khi kích hoạt; xem [huấn luyện](docs/training.md).
- Tất cả kết quả cần con người xác nhận. Score OCR chưa là xác suất đúng; đồng thuận không bảo đảm crop đúng.
- Máy mới tự khôi phục **snapshot đã được chủ dự án cho phép công khai**: 660 khách hàng, 61 ảnh, 37 nhãn, 30 crop train/7 crop validation và 3 artifact TESTING. Không mang theo tài khoản/mật khẩu/phiên cũ; tạo quản trị mới. Xem [dữ liệu đầy đủ](docs/shared-data.md). Dùng `-EmptyDatabase` hoặc `EMPTY_DATABASE=1` nếu muốn cài trống.

[Pipeline](docs/ai-pipeline.md) · [Huấn luyện](docs/training.md) · [Độ tin cậy](docs/ai-reliability.md).

## Vận hành và bảo mật

Docker Compose duy nhất gồm Next.js, FastAPI, PostgreSQL, worker/trainer, hai reader và Nginx. Database/ảnh/model nằm trong ba volume lâu dài; dừng container không xóa data. Migrations và lịch sử Git được giữ để truy vết, không phải các bản ứng dụng cũ phải chạy.

```text
docker compose --project-name elec_man --env-file .env stop
docker compose --project-name elec_man --env-file .env up -d --wait --wait-timeout 300
```

Mặc định chỉ mở HTTP trên loopback. Trước Internet phải cấu hình HTTPS, quyết định dữ liệu dashboard được công khai hay không, backup ngoài máy và giám sát. Snapshot trong data/ đã được cho phép công khai; không commit .env, password, raw dump hoặc dữ liệu mới chưa được phép. Không dùng down -v/volume prune để sửa lỗi.

[Triển khai/cập nhật](docs/deployment.md) · [Bảo mật](docs/security.md) · [Backup/restore](docs/backup-restore.md).

## Phát triển và tài liệu

[Danh mục tài liệu đầy đủ](docs/README.md) · [Cấu trúc source](docs/source-structure.md) · [Phát triển](docs/development.md) · [Kiểm thử](docs/testing.md).

CI kiểm backend, PostgreSQL integration, frontend, AI, Compose, bootstrap/docs và secret policy; CodeQL riêng. Báo cáo theo ngày tại docs/reports không dùng benchmark nhỏ như cam kết accuracy.

Repo chưa có giấy phép mã nguồn tổng quát; thống nhất với chủ dự án trước phân phối lại. Trọng số/dependency có giấy phép riêng.
