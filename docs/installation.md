# Cài đặt và khởi động trên máy mới

Hướng dẫn này dành cho bản mã nguồn tại nhánh `master`. Máy mới có database rỗng, không chứa khách hàng, ảnh, nhãn hoặc mô hình định vị của người phát triển. Bạn có thể nhập khách hàng, tải ảnh và kiểm duyệt ngay sau khi tạo quản trị. Bộ đọc PP-OCR/PARSeq dùng trọng số dựng sẵn; đây không phải cam kết nhận diện đúng mọi công tơ.

## 1. Chuẩn bị

- Git; Docker Engine/Desktop đang chạy với **Linux containers** và Docker Compose có `up --wait`.
- Windows: dùng Docker Desktop theo [hướng dẫn chính thức](https://docs.docker.com/desktop/setup/install/windows-install/). Bật WSL 2/ảo hóa theo yêu cầu của Docker, không chạy chế độ Windows containers.
- Linux: cài Docker Engine và [Compose plugin chính thức](https://docs.docker.com/compose/install/linux/). Dùng Bash để chạy bộ khởi động.
- Cấp đủ RAM/ổ đĩa cho hai bộ đọc CPU. 8 GB RAM dành cho Docker là điểm bắt đầu để thử; 16 GB RAM máy và hàng chục GB đĩa trống thoải mái hơn. Đây là gợi ý triển khai, không phải benchmark hay mức tối thiểu đã chứng nhận.
- Có Internet trong lần build đầu để tải image, package và trọng số. Có thể mất nhiều phút tùy máy/mạng. Không cần cài Python, Node, PostgreSQL hoặc CUDA trên host để **sử dụng** hệ thống qua Docker.

Kiểm tra:

```text
git --version
docker info
docker compose version
```

Nếu `docker info` không kết nối được daemon, mở Docker Desktop hoặc khởi động Docker Engine trước.

## 2. Lấy đúng một bản mã nguồn

```text
git clone https://github.com/hoang23028-lgtm/Elec_Man.git
cd Elec_Man
git branch --show-current
```

Nhánh chính là `master`; lịch sử commit dùng cho truy vết/khôi phục, không phải nhiều bản ứng dụng phải chạy cùng lúc. Không tải lại toàn bộ dự án mỗi lần cập nhật, không sao chép `node_modules` hay volume dữ liệu vào source.

## 3. Khởi động bằng một lệnh

Windows, từ thư mục dự án:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start.ps1
```

`Bypass` chỉ áp dụng tiến trình này, không đổi chính sách toàn máy. Nếu đang dùng PowerShell 7 và chính sách cho phép script, có thể chạy `pwsh -File ./scripts/start.ps1`.

Linux/macOS với Docker tương thích:

```bash
bash scripts/start.sh
```

Bộ khởi động thực hiện:

1. Kiểm tra Docker và tên dự án; nếu đã có container/volume nhưng mất cấu hình, dừng lại để tránh tạo secret sai.
2. Build image backend; tạo `.env` riêng bằng mật khẩu PostgreSQL và khóa session ngẫu nhiên. File đã tồn tại được giữ nguyên, không đổi secret/mật khẩu.
3. Kiểm tra Compose mà không in cấu hình chứa secret; build các image còn lại, gồm trọng số hai reader.
4. Chờ PostgreSQL; chạy migration Alembic; chờ backend, frontend, reader và Nginx sẵn sàng.
5. Nếu chưa có SUPER_ADMIN chưa bị xóa mềm, yêu cầu mật khẩu cho tài khoản `admin` (12–256 ký tự). Mật khẩu chỉ được truyền tạm qua môi trường tiến trình, không nằm trong đối số lệnh hay được ghi vào `.env`.
6. In trạng thái hoàn tất. Mở [http://localhost/](http://localhost/), đăng nhập tài khoản vừa tạo.

Khởi động lại không đổi mật khẩu tài khoản đã có. Tài khoản SUPER_ADMIN đang bị khóa vẫn được tính là đã tồn tại; bộ cài không tạo tài khoản để vượt khóa đó. Nếu tên `admin` đã có nhưng không có SUPER_ADMIN, chọn tên khác, không tự nâng quyền người xem.

Chọn tên quản trị/cổng khác cho **lần cài mới**:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start.ps1 -Username quantri -Port 8080
```

```bash
ADMIN_USERNAME=quantri NGINX_HTTP_PORT=8080 bash scripts/start.sh
```

Khi đã có `.env`, đổi cổng/origin trực tiếp trong cấu hình theo [tài liệu cấu hình](configuration.md); tham số cài mới không viết đè cấu hình cũ. Chỉ sử dụng `-SkipBuild` / `SKIP_BUILD=1` khi các image cần thiết đã được build trên máy.

## 4. Kiểm tra sau cài

```text
docker compose --project-name elec_man --env-file .env ps -a
curl http://localhost/api/v1/health/ready
```

Đổi URL nếu chọn cổng khác. Các tiến trình lâu dài phải chạy; backend/frontend/readers/nginx có healthcheck phải healthy. `migrate`, `storage-init`, `model-init` **Exited (0)** là bình thường vì chạy một lần.

Đăng nhập rồi kiểm tra sáu trang theo vai trò: Tổng quan, Vận hành, Các lô dữ liệu, Quản trị, Vòng đời mô hình, Truy vết. Không có dữ liệu trên dashboard của máy mới là bình thường.

## 5. Nhập dữ liệu đầu tiên

1. Quản trị → Khách hàng → nhập JSON hoặc thêm thủ công. Dùng [examples/customers.json](../examples/customers.json) nếu muốn thử với **dữ liệu giả**.
2. Vận hành → chọn ảnh JPG/PNG/WebP → tải lên và xử lý.
3. Chọn ảnh trong Cần xử lý; kiểm tra vùng công tơ, vùng chỉ số và chuỗi số nguyên. Lưu nhãn có thể thực hiện trước khi có mã khách hàng.
4. Xác nhận mã chuẩn trong database, chỉ số và tháng ghi điện. Chỉ thao tác xác nhận mới tạo dữ liệu tháng chính thức.
5. Quản trị → Chỉ số tháng/xuất báo cáo → chọn tháng/năm → tải JSON và Excel.

Xem [hướng dẫn sử dụng](usage.md) và [huấn luyện](training.md) trước khi thu thập nhãn hàng loạt.

## 6. Dừng, bật lại và cập nhật

```text
docker compose --project-name elec_man --env-file .env stop
docker compose --project-name elec_man --env-file .env up -d --wait --wait-timeout 300
```

Lệnh dừng không xóa volume. Không dùng `down -v`, `volume prune` hoặc xóa thư mục dữ liệu để xử lý lỗi. Cập nhật code có migration phải sao lưu và làm trong cửa sổ bảo trì theo [triển khai](deployment.md), không coi chạy bộ cài là thay thế backup.

## 7. Các lỗi thường gặp

| Triệu chứng | Kiểm tra và xử lý |
|---|---|
| Docker daemon không chạy | Mở Docker Desktop/Engine, kiểm tra Linux containers và WSL/ảo hóa |
| Cổng 80 đã được dùng | Cài mới với cổng 8080; nếu đã có cấu hình, đổi NGINX_HTTP_PORT và FRONTEND_ORIGIN đồng bộ |
| Build reader lỗi tải trọng số | Kiểm tra Internet/proxy/đĩa, xem lỗi build; chạy lại tận dụng cache. Không thay bằng mock mà vẫn gọi là AI thật |
| Reader bị kill/OOM | Tăng RAM Docker, giảm tác vụ đồng thời; xem trạng thái container. Timeout không tự chứng minh nhãn sai |
| 502 Bad Gateway | Xem `ps -a`, log backend/frontend/nginx và readiness; đợi migration/readers hoàn tất, không xóa volume |
| Đăng nhập sai | Dùng tài khoản đã tạo; đăng ký mới là VIEWER chưa kích hoạt. Sau nhiều lần sai, chờ cửa sổ rate limit |
| CSRF/origin hoặc cookie lỗi | Truy cập cùng URL với FRONTEND_ORIGIN; không đổi qua lại localhost/127.0.0.1, đăng nhập lại |
| Dự án có dữ liệu nhưng thiếu .env | Khôi phục cấu hình gốc từ kho bảo mật. Không tạo mật khẩu PostgreSQL mới cho volume cũ |
| 409 hoặc 412 khi lưu | 409: xung đột dữ liệu/tháng; 412: ảnh đã thay đổi từ phiên khác. Làm mới, kiểm tra rồi nhập lại; không ghi đè mù |

```text
docker compose --project-name elec_man --env-file .env logs --tail 100 backend worker trainer
docker compose --project-name elec_man --env-file .env logs --tail 100 reader-ppocr reader-parseq nginx
```

Không gửi `.env`, mật khẩu, nội dung database hoặc ảnh khách hàng vào issue/chat công khai. Quy tắc chờ dịch vụ dựa trên [Docker Compose up](https://docs.docker.com/reference/cli/docker/compose/up/).
