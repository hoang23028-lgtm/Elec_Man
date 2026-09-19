# Bảo mật và xác thực

Hệ thống sử dụng một tài khoản quản trị viên, mật khẩu băm Argon2id, phiên làm việc không trong suốt phía máy chủ và cookie HttpOnly. Cơ sở dữ liệu chỉ lưu giá trị băm SHA-256 của phiên và token CSRF. Cookie có thuộc tính `Secure` trong production và dùng `SameSite=Strict`.

Mọi endpoint thay đổi trạng thái có xác thực đều yêu cầu `X-CSRF-Token` được trả về khi đăng nhập. Frontend chỉ giữ token CSRF không phải thông tin đăng nhập này trong bộ nhớ, không lưu vào localStorage. Số lần đăng nhập được giới hạn trong bộ nhớ ở mức năm lần cho mỗi tổ hợp IP/tên đăng nhập trong 15 phút, phù hợp với phạm vi một máy chủ.

Tạo quản trị viên sau khi áp dụng migration:

```powershell
$env:ADMIN_INITIAL_PASSWORD = "mat-khau-dai-va-duy-nhat"
docker compose exec backend python -m app.scripts.init_admin --username admin_operator
Remove-Item Env:ADMIN_INITIAL_PASSWORD
```

Trong production, đặt `SESSION_SECRET` thành giá trị ngẫu nhiên duy nhất dài ít nhất 32 ký tự. Quá trình khởi động sẽ từ chối giá trị mẫu trong production. Không bao giờ commit tệp `.env`.
