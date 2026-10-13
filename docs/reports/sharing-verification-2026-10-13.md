# Xác minh bản chia sẻ GitHub — 13/10/2026

> Báo cáo theo ngày. Hướng dẫn hiện hành ở [danh mục tài liệu](../README.md).

## Thay đổi đóng gói

- Một nhánh chia sẻ chuẩn master, một Compose cho hệ thống; không force-push hoặc xóa lịch sử.
- Frontend được tách app shell/auth/hook nghiệp vụ, backend có query/policy/revision/file transaction dùng chung; không giữ implementation HOG đọc từng ô trong pipeline mới.
- Bộ khởi động Windows/Linux tạo env riêng, secret ngẫu nhiên, build, migration/readiness và tạo SUPER_ADMIN không có mật khẩu mặc định.
- Init quản trị idempotent, có khóa PostgreSQL, không nâng quyền VIEWER trùng username hoặc vượt SUPER_ADMIN bị khóa.
- Cổng HTTP local có thể cấu hình; env giới hạn upload/worker/retry được truyền đúng dịch vụ. Nginx có healthcheck đường vào.
- Verify backup dùng chung Python: checksum/manifest và loại đường dẫn/link/member nguy hiểm trước giải nén. Linux backup kiểm owner volume và project.
- Tài liệu hiện hành tách khỏi báo cáo theo ngày; tên Markdown chuẩn kebab-case, có index/cài đặt/sử dụng/cấu hình/phát triển/triển khai chi tiết.
- Git bỏ qua env/TLS/data/ảnh/nhãn/backup/model/cache/build, chỉ có mẫu khách hàng giả; checker link và secret policy nằm trong CI.

## Kết quả tại máy kiểm tra

| Phạm vi | Kết quả |
|---|---|
| Backend unit/regression | 776 passed; 2 warning deprecation của TestClient/httpx |
| PostgreSQL integration tách biệt | 24 passed; toàn bộ 28 migration từ database trống |
| AI image build từ source hiện tại | 37 passed |
| Frontend logic thuần | 15 passed |
| Frontend typecheck/lint/build | Đạt |
| Ruff check/format | Đạt |
| Markdown local links, diff whitespace, secret pattern | Đạt; không là bảo đảm phát hiện mọi secret/PII |
| PowerShell startup | Cài mới thành công với database/volume/cổng riêng |
| Shell startup/backup/verifier | Kiểm tra cú pháp Bash/sh đạt; chưa chạy fresh install Linux thực tế tại máy này |

Tổng 852 kiểm thử tự động đạt. Con số chỉ phản ánh lần chạy này, không thay số của commit tương lai hoặc kết quả GitHub Actions.

## Fresh-install dùng dữ liệu giả

Project elec_share_verify, HTTP loopback cổng 60680, file env riêng; không dùng database hoặc volume production. Build reader thật PP-OCRv6/PARSeq-tiny; các dịch vụ có healthcheck đều healthy, tiến trình worker/trainer chạy, init/migrate Exited(0).

Đã kiểm tra HTTP trang chủ/readiness, API chưa đăng nhập trả 401, đăng nhập quản trị/cookie HttpOnly, nhập một khách hàng DEMO giả, upload ảnh JPEG tổng hợp và đưa hàng đợi. Worker OCR thật hoàn tất; lưu vùng công tơ/nhãn số chưa cần mã, tải lại còn LABELED và đúng nhãn, xác nhận mã/tháng, xem ảnh và xuất JSON/Excel đúng bảy trường, một bản ghi tháng. Đã nhập đúng số thủ công, không coi ảnh tổng hợp là benchmark độ chính xác.

Chạy starter lần hai giữ cấu hình và mật khẩu gốc, không reset bằng env password mới. Có project/volume nhưng thiếu env thì dừng trước tạo cấu hình thay thế.

Backup dữ liệu giả và verify manifest/archive đạt. Diễn tập restore ở PostgreSQL/thư mục tạm: một khách hàng, hai ảnh, một chỉ số tháng; hash tất cả bảy file kho ảnh khớp; migration head 20261012_0028. Không gắn volume production; tài nguyên diễn tập tự dọn.

## Giới hạn

- Lần CI đầu sau push: backend/frontend/AI/Compose và CodeQL đạt, hai bước lint tools/integration lỗi do Ruff runner mới có default rules khác bản local. Đã cố định Ruff 0.17.0, thêm cấu hình root rõ ràng, chuẩn hóa import và check=False cho subprocess được kiểm mã trả về. Kết quả CI của commit sửa phải xem trực tiếp trên GitHub, không dùng trạng thái của commit trước.
- Không chạy thao tác ghi/nhãn/xác nhận/restore trên dữ liệu thật; localhost đang sử dụng được giữ nguyên.
- Không chứng minh accuracy trên công tơ thực, tải lớn, Linux/macOS fresh install hoặc DNS/TLS Internet bằng kiểm tra Windows local này.
- Trọng số reader pretrained được tải khi build; fine-tune deep reader chưa có trong pipeline. Model định vị riêng/ảnh/khách hàng không kèm Git.
- Tự động xác nhận vẫn khóa; dashboard công khai cần quyết định privacy trước Internet. Backup offsite/mã hóa/giám sát do triển khai cấu hình.
- Giữ bản ghi model và báo cáo cũ để truy vết, không giữ code nhận dạng kém làm đường vận hành song song.
