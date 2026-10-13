# Bảo mật, dữ liệu riêng và giới hạn

## Xác thực và quyền

Mật khẩu băm Argon2id. Session opaque phía server, database lưu HMAC-SHA-256 token bằng SESSION_SECRET; đổi khóa thu hồi phiên cũ. Cookie HttpOnly, SameSite=Strict, Secure trong production, TTL mặc định 8 giờ. CSRF token chỉ trong bộ nhớ frontend, không localStorage; mọi thay đổi có xác thực yêu cầu X-CSRF-Token.

Đăng nhập giới hạn theo IP+tên (5 lần sai/15 phút) và IP (30 lần sai/15 phút). Đăng ký giới hạn 5 yêu cầu/IP/giờ, phản hồi không tiết lộ username tồn tại; luôn tạo VIEWER chưa kích hoạt. Rate limiter trong bộ nhớ phù hợp một API process, không phải limiter phân tán. Restart process làm mất bộ đếm; scale replica cần kho limiter chung.

Backend kiểm tra role cho từng nhóm API. VIEWER/guest không dùng nghiệp vụ; ADMIN không train/sửa hệ thống; SUPER_ADMIN có quyền hệ thống. Không tự khóa/xóa/hạ quyền hoặc xóa SUPER_ADMIN hoạt động cuối cùng. Xem [quyền](roles.md).

Bộ khởi động nhập password quản trị không có giá trị mặc định, truyền env tạm không argv, không ghi password vào file/log. Không sử dụng script bootstrap làm bypass khóa/reset password.

## Upload, đường dẫn và database

Chỉ JPEG/PNG/WebP sau kiểm MIME, signature, giải mã, dung lượng và pixel count; JSON khách hàng tối đa 10 MB/10.000 dòng. Schema server validate chuỗi, số, tháng, đa giác, role và trạng thái. Mã/names từ người dùng không dùng làm đường dẫn gốc tùy ý.

File gốc UUID bên dưới STORAGE_ROOT, model dưới MODELS_ROOT có resolve/containment/checksum. Xem ảnh/export yêu cầu quyền; kho volume không được static serve. Excel vô hiệu hóa ký tự đầu công thức. SQLAlchemy bind parameters; không ghép input thành SQL. SQL restore là mã thực thi: chỉ dùng backup từ nguồn tin cậy.

Nhãn chưa xác nhận không vào bảng chỉ số tháng. Revision và unique(customer,month) chống ghi đè stale/trùng tháng. Log hành động lưu trước/sau nhưng không lưu token/password.

## Mạng, HTTPS và headers

Compose tách edge/application/data; PostgreSQL không publish cổng và không dùng chung network với frontend/nginx. Reader không truy cập database hoặc ảnh trên volume. Python runtime filesystem chỉ đọc, quyền thấp, cap_drop ALL, no-new-privileges; init volume chạy riêng một lần.

Local HTTP chỉ 127.0.0.1. Production bắt buộc HTTPS với cấu hình/CA hợp lệ; không chỉ đặt ENFORCE_HTTPS=true mà bỏ triển khai TLS. Khởi động production từ chối secret/mật khẩu mẫu, ALLOWED_HOSTS=* và origin HTTP. Tài liệu API tự động tắt trong production.

CORS chỉ FRONTEND_ORIGIN; proxy không tin X-Forwarded-For/Proto tự gửi từ client. Nginx/API có chống MIME sniffing/clickjacking, CSP và hạn chế camera/mic/location. CSP còn cho unsafe-inline để tương thích Next.js/style hiện tại; không tuyên bố CSP nghiêm ngặt tuyệt đối. HSTS chỉ giữ khi TLS/subdomain đã kiểm tra.

## Log, backup và repo công khai

API lỗi bất ngờ trả thông báo chung cùng request_id; log server có loại lỗi và thông tin định danh tác vụ, không trả stacktrace/DSN cho người dùng. Docker log xoay 10 MB × 5/container; INFO mặc định. Audit có dữ liệu khách hàng/nghiệp vụ, chỉ SUPER_ADMIN xem.

.env, TLS, backups, log riêng và thông tin xác thực **không được commit**. Ngoại lệ dữ liệu: snapshot khách hàng/ảnh/nhãn/model tại data/ được chủ dự án xác nhận có quyền công khai ngày 13/10/2026, đã bỏ tài khoản có thể đăng nhập, hash thật, sessions, audit auth và IP. Xem [phạm vi dữ liệu](shared-data.md). Không tự áp dụng cho dữ liệu mới. Quét pattern secret chỉ bắt một số token/key phổ biến, không thay review thủ công hoặc bảo đảm bắt mọi PII. Nếu secret từng công khai, phải thu hồi/rotate; xóa file mới không xóa bản cũ trong Git.

Backup chứa dữ liệu nhạy cảm, không tự mã hóa. Mã hóa nơi lưu, phân quyền, bản ngoài host, retention, lịch chạy/cảnh báo và thử restore là nhiệm vụ người triển khai; script chưa tự cung cấp dịch vụ giám sát hoặc offsite. Xem [backup](backup-restore.md).

Dashboard công khai có thể lộ mã/số liệu khách hàng theo thiết kế hiện tại. Chốt quyền công khai hoặc bổ sung kiểm soát/ẩn danh trước Internet. Không thể cam kết “không rò rỉ” chỉ từ test source hoặc trạng thái CI xanh.

## Kiểm tra định kỳ

Kiểm CI/CodeQL, secret policy, npm audit và cập nhật digest/dependency có thử nghiệm. Xác minh API thiếu quyền/CSRF, session bị thu hồi, upload, path traversal và headers/cookie trên hạ tầng thật. Theo dõi health, 5xx, LOGIN_FAILED, job/train FAILED và dung lượng. Không chạy kiểm thử ghi dữ liệu lên production.
