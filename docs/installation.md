# Cài đặt trên máy khác

## Yêu cầu

- Windows 10/11 hoặc Linux 64-bit.
- Git.
- Docker Desktop (Windows) hoặc Docker Engine kèm Docker Compose v2 (Linux).
- Tối thiểu 8 GB RAM và khoảng 10 GB dung lượng trống. OCR chạy tốt hơn khi có từ 4 lõi CPU.

Không cần cài riêng Python, Node.js, PostgreSQL hay Tesseract vì các thành phần này nằm trong container.

## 1. Tải source code

```powershell
git clone https://github.com/hoang23028-lgtm/Elec_Man.git
Set-Location Elec_Man
Copy-Item .env.example .env
```

Trên Linux, thay lệnh cuối bằng `cp .env.example .env`.

## 2. Tạo cấu hình riêng cho máy mới

Tạo hai chuỗi ngẫu nhiên bằng PowerShell:

```powershell
[Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32)).ToLower()
[Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32)).ToLower()
```

Trên Linux có thể chạy `openssl rand -hex 32` hai lần. Mở `.env` và:

1. Dùng chuỗi thứ nhất cho `POSTGRES_PASSWORD` và thay đúng phần mật khẩu trong `DATABASE_URL`.
2. Dùng chuỗi thứ hai cho `SESSION_SECRET`.
3. Giữ `NGINX_BIND_ADDRESS=127.0.0.1` nếu chỉ dùng trên chính máy đó.
4. Nếu truy cập qua tên miền/reverse proxy, thêm tên miền vào `ALLOWED_HOSTS`; không dùng `*` trong production.
5. Đặt `APP_ENV=production` khi triển khai chính thức.

Không gửi hoặc commit tệp `.env`. Tệp này đã được `.gitignore` loại trừ.

## 3. Build và khởi động

```powershell
docker compose up -d --build
docker compose ps
```

Container `migrate` tự áp dụng migration trước khi backend khởi động. Chờ backend chuyển sang `healthy`, sau đó mở `http://localhost/`. Kiểm tra sẵn sàng:

```powershell
Invoke-RestMethod http://localhost/api/v1/health/ready
```

## 4. Tạo tài khoản quản trị đầu tiên

PowerShell (mật khẩu không được ghi vào lịch sử lệnh):

```powershell
$securePassword = Read-Host "Mật khẩu quản trị (tối thiểu 12 ký tự)" -AsSecureString
$credential = [PSCredential]::new("admin", $securePassword)
$plainPassword = $credential.GetNetworkCredential().Password
docker compose exec -e "ADMIN_INITIAL_PASSWORD=$plainPassword" backend python -m app.scripts.init_admin --username admin_operator
Remove-Variable plainPassword, credential, securePassword
```

Linux:

```bash
read -rsp "Mật khẩu quản trị: " ADMIN_PASSWORD && echo
docker compose exec -e ADMIN_INITIAL_PASSWORD="$ADMIN_PASSWORD" backend python -m app.scripts.init_admin --username admin_operator
unset ADMIN_PASSWORD
```

Đăng nhập bằng tài khoản này. Các tài khoản tiếp theo được quản lý tại **Quản trị → Quản lý tài khoản**.

## 5. Cập nhật phiên bản sau này

Sao lưu trước khi cập nhật, sau đó tải code và build lại:

```powershell
.\scripts\backup.ps1
git pull --ff-only origin master
docker compose up -d --build
docker compose ps
```

Không sao chép volume PostgreSQL đang chạy bằng File Explorer. Khi chuyển cả dữ liệu sang máy khác, dùng quy trình trong [backup-restore.md](backup-restore.md).

## Khắc phục nhanh

- Không mở được trang: chạy `docker compose ps` và `docker compose logs --tail 100 backend nginx`.
- Backend không khởi động ở production: kiểm tra `SESSION_SECRET`, mật khẩu mẫu, `DATABASE_URL` và `ALLOWED_HOSTS`.
- Cổng 80 đang được sử dụng: dừng dịch vụ chiếm cổng hoặc đổi cổng phía host trong `docker-compose.yml`.
- Máy khác trong LAN không truy cập được: đây là mặc định an toàn. Chỉ mở bind ra mạng sau khi đã cấu hình firewall và HTTPS/reverse proxy.
