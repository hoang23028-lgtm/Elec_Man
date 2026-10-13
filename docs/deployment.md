# Triển khai, cập nhật và chia sẻ bản chuẩn

## 1. Bản chia sẻ

Repo chính: [hoang23028-lgtm/Elec_Man](https://github.com/hoang23028-lgtm/Elec_Man), nhánh master. Một checkout và một docker-compose.yml là bản vận hành chuẩn; không chạy folder bản cũ song song hoặc đẩy dữ liệu private lên repo. Lịch sử Git/migrations vẫn được giữ.

Máy mới làm theo [cài đặt](installation.md). Chia sẻ mã nguồn không chuyển database/ảnh/nhãn của máy cũ. Nếu cần chuyển dữ liệu, dùng backup riêng được bảo vệ theo [hướng dẫn backup](backup-restore.md), không Git.

## 2. Cập nhật máy đang có dữ liệu

1. Chốt cửa sổ bảo trì, ngăn người dùng sửa dữ liệu và dừng writer.
2. Backup đủ database/storage/models, xác minh, lưu cấu hình secret riêng và ghi commit đang chạy.
3. Kiểm tra working tree không có sửa local chưa lưu. Nếu có, commit riêng hoặc đối chiếu; không reset --hard.
4. Lấy bản mới bằng fast-forward, build, migration rồi khởi động và kiểm tra.
5. Nếu lỗi, giữ writer dừng; xem log/migration/backup. Rollback code không tự rollback schema và không tự phục hồi data.

Ví dụ cho project mặc định, từ root repo:

```text
docker compose --project-name elec_man --env-file .env stop nginx frontend backend worker trainer
```

Tạo backup bằng script phù hợp OS ở [backup-restore.md](backup-restore.md), **xác minh thành công rồi** tiếp tục:

```text
git pull --ff-only origin master
docker compose --project-name elec_man --env-file .env build
docker compose --project-name elec_man --env-file .env run --rm --no-deps migrate
docker compose --project-name elec_man --env-file .env up -d --wait --wait-timeout 300
docker compose --project-name elec_man --env-file .env ps -a
```

PostgreSQL phải còn chạy khi run migration. Không đổi project name, POSTGRES_PASSWORD hoặc xóa volume để làm migration chạy được. Dùng cấu hình migration production phù hợp khi chuyển HTTP→HTTPS.

## 3. Local không phải production Internet

Mặc định HTTP loopback. Để công bố Internet cần domain/DNS, chứng thư, firewall, chính sách dữ liệu công khai, backup ngoài máy và giám sát. Bộ cài local **không** tự mua domain, mở port hoặc triển khai cloud.

Dashboard công khai theo yêu cầu sản phẩm có thể hiển thị mã khách hàng/số liệu tiền điện. Chưa quyết định quyền công khai/ẩn danh/đăng nhập thì **không mở Internet** với dữ liệu thật.

## 4. Cấu hình HTTPS tại Nginx của dự án

Mẫu: [docker/nginx.https.conf.example](../docker/nginx.https.conf.example). Thay domain minh họa bằng domain sở hữu; chuẩn bị fullchain.pem/privkey.pem có quyền đọc phù hợp. Không commit khóa TLS hoặc file env.

Tạo **file override riêng trên máy chủ**, không phải một bản source mới. File compose.production.yaml có thể dùng phần sau sau khi đặt domain và chứng thư:

```yaml
services:
  nginx:
    ports: !override
      - "0.0.0.0:80:80"
      - "0.0.0.0:443:443"
    volumes: !override
      - ./docker/nginx.production.conf:/etc/nginx/conf.d/default.conf:ro
      - ./tls:/etc/nginx/tls:ro
```

Tag !override yêu cầu Compose hỗ trợ; kiểm tra config --quiet trước, không triển khai cấu hình merge vô tình giữ thêm port HTTP local. Sao chép/chỉnh mẫu HTTPS thành nginx.production.conf, lưu TLS ngoài Git. Nginx healthcheck loopback của cấu hình HTTP cần đổi để kiểm tra HTTPS với Host/domain và CA hợp lệ hoặc endpoint nội bộ tương ứng; **không vô hiệu hóa kiểm tra chứng thư cho lưu lượng người dùng**.

Trong .env: APP_ENV=production, ENFORCE_HTTPS=true, FRONTEND_ORIGIN=https://domain-cua-ban, ALLOWED_HOSTS=domain-cua-ban. Secret mạnh và mật khẩu database khớp. Nếu TLS kết thúc tại reverse proxy ngoài, cấu hình forwarded headers/trust boundary chính xác; Nginx HTTP mẫu hiện gửi X-Forwarded-Proto theo scheme nó nhận, không tự tin header do client gửi.

Dùng đúng hai -f cho mọi lệnh production:

```text
docker compose -p elec_man --env-file .env -f docker-compose.yml -f compose.production.yaml config --quiet
```

Mẫu TLS đã có HSTS includeSubDomains; kiểm tra toàn bộ subdomain có TLS trước khi giữ tùy chọn này. Mở firewall chỉ 80 chuyển hướng và 443; không mở PostgreSQL/backend/readers. Xem [bảo mật](security.md).

## 5. Gate trước go-live

- CI/test đạt trên commit triển khai; kiểm tra thay đổi dependency/digest trước nâng cấp.
- Migration từ đầu và đường nâng cấp có backup; không xem build thành công là API sẵn sàng.
- Thử guest/VIEWER/ADMIN/SUPER_ADMIN, CSRF, logout/session expiry, upload sai loại/quá lớn, xung đột tháng/revision.
- Xác minh HTTPS thật, redirect 308, cookie HttpOnly/Secure/SameSite, CORS đúng origin và security headers qua proxy.
- Diễn tập backup/restore tách biệt; mã hóa, chuyển bản ra ngoài host, retention và cảnh báo thất bại.
- Theo dõi health/5xx/job/train lỗi, RAM/đĩa và queue age; không chạy DEBUG với dữ liệu thật.
- Giữ xác nhận thủ công, đối chiếu chính sách giá điện với nghiệp vụ trước phát hành báo cáo thu tiền.

Hướng dẫn này không chứng nhận pháp lý hóa đơn hoặc độ chính xác AI. Báo cáo kiểm tra thực tế được lưu ở [danh mục tài liệu](README.md).

Mô tả merge !override xem [Docker Compose merge](https://docs.docker.com/reference/compose-file/merge/).
