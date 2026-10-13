# Xác minh bản công khai có dữ liệu — 13/10/2026

> Báo cáo theo ngày, bổ sung sau [bản chia sẻ source](sharing-verification-2026-10-13.md). Chủ dự án xác nhận giữ repo PUBLIC và có quyền chia sẻ khách hàng, ảnh/nhãn thật. Hướng dẫn hiện hành ở [dữ liệu chia sẻ](../shared-data.md).

## 1. Bản chụp đã được phép công khai

Snapshot tạo lúc **14:31:20 ngày 13/10/2026 (Asia/Bangkok, UTC+7)**, migration `20261012_0028`. Có 179 tệp, 19.574.111 byte. Manifest ghi checksum SHA-256 và dung lượng từng payload; database JSON có checksum `87f41b20cd106995f4edcf9718b078cc1e8a80f3537897e6feed609801c7528d`.

| Thành phần | Số lượng |
|---|---:|
| Khách hàng | 660 |
| Lô dữ liệu / ảnh gốc | 11 / 61 |
| Kết quả AI / công việc OCR lịch sử | 61 / 61 |
| Nhãn đã lưu / ảnh từ chối | 37 / 24 |
| Chỉ số tháng đã xác nhận | 0 |
| Thay đổi thủ công / audit nghiệp vụ | 123 / 483 |
| Phiên huấn luyện / artifact TESTING | 1 / 3 |
| Nhãn JSONL / crop train / crop validation | 37 / 30 / 7 |

Giữ nguyên chỉ số, số 0 đầu, revision, vùng chỉ số và vùng công tơ; không dùng OCR để thay đáp án khi xuất. Kho storage/model được sao chép với checksum khớp metadata nguồn. Artifact HOG lịch sử chỉ giữ truy vết, không phục hồi đường nhận dạng cũ hoặc kích hoạt model.

## 2. Loại thông tin xác thực

- Không xuất bảng sessions, tên đăng nhập/hash gốc, secret môi trường, khóa TLS hoặc raw SQL dump.
- Bốn actor giữ UUID phục vụ foreign key, đổi tên thành `snapshot_actor_UUID`, VIEWER/inactive, hash sentinel `!` không hợp lệ. Đây không phải bốn tài khoản vận hành có thể đăng nhập.
- Loại audit đăng nhập/tài khoản/mật khẩu, bỏ IP và credential lồng trong JSON; không xuất lỗi riêng hoặc worker identity.
- Soát payload với session secret và mật khẩu PostgreSQL thực trong bộ nhớ; không ghi/in các giá trị đó. Checker tĩnh kiểm token/key phổ biến và file `.env`/`.pem`/`.key`/`.log`.
- Tắt tự khởi động train trong bản sao; không sửa cấu hình hoặc nhãn của hệ thống nguồn.

Dữ liệu khách hàng và ảnh thật **không được ẩn danh**; chúng được công khai đúng phạm vi đã được chủ dự án cho phép. Quét secret không chứng minh bắt mọi thông tin nhạy cảm. Không áp dụng chấp thuận cho dữ liệu mới.

## 3. Thử khôi phục trên máy mới

Windows/Docker, project riêng `elec_data_verify`, env riêng, cổng loopback 60681 và ba volume riêng. Build ứng dụng/readers, chạy đủ 28 migration, seed Exited(0), tạo SUPER_ADMIN mới. Không gắn volume production vào máy thử.

Qua API đã xác minh:

- Có 660 khách hàng, 61 kết quả, đúng 37 LABELED/24 REJECTED/0 CONFIRMED.
- Đọc toàn bộ 61 ảnh qua endpoint preview; hash nội dung khớp ảnh gốc byte-for-byte.
- Chỉ số, trạng thái, revision và hai polygon của cả 61 kết quả khớp JSON nguồn.
- Có ba model lịch sử, 37 mẫu train đủ điều kiện gắn nhãn và `auto_start_enabled=false`.
- Chỉ tài khoản admin mới active; bốn actor inactive. Thử đăng nhập actor trả 401.
- Chạy seed lần hai với module kiểm tra hiện hành: giữ database, không ghi đè/nhân đôi dữ liệu.

Thử riêng project `elec_empty_verify`: đặt `IMPORT_SHARED_DATA=false`, migration/seed thành công, số khách hàng và tài khoản đều bằng 0 trước bootstrap. Không chạy lại toàn ứng dụng ở chế độ này.

Đã kiểm tra owner rồi dọn container/network/volume và env của hai project thử. Dữ liệu thử có thể tạo lại từ snapshot; database/storage/model đang dùng tại localhost không bị xóa. Readiness localhost trả HTTP 200 sau bảo trì/xác minh.

## 4. Kiểm thử phần mềm

| Phạm vi | Kết quả |
|---|---|
| Backend unit/regression | 798 passed, 2 warning deprecation TestClient/httpx |
| PostgreSQL integration riêng | 24 passed, 1 warning TestClient/httpx |
| AI với source hiện hành mount chỉ đọc trong test image | 37 passed |
| Frontend logic | 15 passed |
| Frontend typecheck / lint / production build | Đạt |
| Ruff 0.17.0 check / format | Đạt |
| Snapshot hashes / credentials / đường dẫn / metadata | Đạt |
| Link Markdown / secret policy / diff whitespace | Đạt |

Tổng **874 bài kiểm thử tự động đạt** tại máy này, gồm 22 regression mới cho snapshot. Không coi kiểm thử logic là benchmark accuracy. CI/CodeQL phải xem kết quả trên đúng commit GitHub; báo cáo này không dùng trạng thái của commit cũ.

## 5. Giới hạn và sử dụng

- Chỉ có 37 mẫu, dưới ngưỡng mặc định 200. Chưa có nhóm công tơ xác minh cho cả 37 mẫu; validation 7 ảnh không phải holdout độc lập. Không hạ gate/auto-confirm để tạo kết quả đẹp.
- Reader pretrained PP-OCR/PARSeq tải lúc build. Fine-tune deep reader chưa được pipeline tự thực hiện; artifact TESTING không chứng minh AI đạt chuẩn sản xuất.
- Snapshot là dữ liệu tại mốc chụp, không tự đồng bộ dữ liệu mới, không sao lưu nguyên thông tin xác thực. Backup riêng vẫn cần cho sử dụng thực tế.
- Khôi phục đầy đủ được thử trên Windows/Docker. Chưa thử fresh install Linux/macOS thực tế hoặc deploy DNS/TLS Internet trong lần này.
- Đây là dữ liệu công khai: người khác có thể tải/fork. Không thu hồi được mọi bản sao bằng xóa commit mới hoặc đổi visibility sau này.

Một checkout master, một snapshot hiện hành, một Compose; giữ lịch sử Git và migration. Xem [cài đặt](../installation.md) để chạy có dữ liệu hoặc cài trống.
