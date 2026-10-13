# Dữ liệu công khai và khôi phục bản đầy đủ

## 1. Phạm vi và quyết định công khai

Ngày 13/10/2026 chủ dự án xác nhận giữ Elec_Man PUBLIC và có quyền công khai dữ liệu thật. Bản hiện tại có dữ liệu tại [data/snapshot](../data/snapshot/manifest.json); secret, session và tài khoản cũ không được công khai. Không dùng sự chấp thuận này cho dữ liệu mới chưa được chủ dữ liệu cho phép.

| Thành phần | Nội dung |
|---|---|
| database.json | Khách hàng, lô/ảnh, kết quả AI, nhãn/revision, thay đổi thủ công, registry/train history, audit nghiệp vụ và cấu hình đã lọc |
| storage/ | Toàn bộ kho ảnh gốc/thumbnail/phái sinh/báo cáo hiện có, giữ đường dẫn tương đối |
| models/ | Ba file NPZ và đường dẫn/checksum khớp registry, giữ TESTING |
| training/labels.jsonl | Metadata ảnh, nhãn số và hai vùng đã lưu, không đổi đáp án |
| training/sequence/ | Crop phối cảnh, train.tsv, validation.tsv và manifest crop |
| manifest.json | Phiên bản định dạng, migration, số bản ghi, SHA-256/dung lượng từng tệp |

Không có dữ liệu tháng chính thức tại mốc chụp; nhãn chưa xác nhận vẫn LABELED. Không biến nhãn thành hóa đơn/chỉ số tháng để làm dashboard có số.

Các bản ghi actor được thay tên snapshot_actor_UUID, VIEWER/inactive và sentinel hash không hợp lệ. UUID giữ nguyên để foreign key/audit/eligibility nhãn không đứt. Không thể đăng nhập bằng mật khẩu cũ, không nhập sessions, không giữ IP/audit xác thực. Tự động train tắt trong bản nhập; job/phiên đang hoạt động nếu có được chuyển CANCELLED. Đây là bản chia sẻ nghiệp vụ an toàn hơn dump toàn database thô, **không** là backup nguyên trạng toàn thông tin xác thực.

## 2. Máy mới: chạy một lệnh có sẵn dữ liệu

Clone master, mở Docker, từ root repo:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start.ps1
```

```bash
bash scripts/start.sh
```

Sau PostgreSQL/migration, dịch vụ seed kiểm tra manifest và chỉ nhập khi database chưa có tài khoản hoặc dữ liệu nghiệp vụ. Seed chép kho tệp sang volume mới, nhập JSON bằng SQLAlchemy trong transaction, giữ nhãn/UUID/revision rồi tạo quản trị mới theo mật khẩu bạn nhập. Không thực thi SQL từ payload JSON.

Chờ seed Exited(0), backend/frontend/readers/nginx healthy; đăng nhập admin mới. Quản trị thấy 660 khách hàng; Vận hành thấy 37 ảnh cần xử lý đã gắn nhãn và 24 ảnh từ chối; Vòng đời mô hình thấy 37 mẫu/ngưỡng mặc định 200. Không cần import lại ảnh hoặc gắn nhãn lại.

Lần build đầu vẫn tải trọng số pretrained PP-OCR/PARSeq qua Internet. Trọng số nền được đóng trong image, không nhân bản cache nhiều GB vào Git. Các NPZ trong snapshot là artifact lịch sử TESTING, không chứng minh bộ định vị đạt gate mới; HOG artifact chỉ giữ truy vết, không được runtime mới kích hoạt.

## 3. Cài database trống hoặc giữ dữ liệu riêng

Windows cài mới không nhập snapshot:

```powershell
./scripts/start.ps1 -EmptyDatabase
```

Linux:

```bash
EMPTY_DATABASE=1 bash scripts/start.sh
```

Hoặc đặt IMPORT_SHARED_DATA=false trong .env. Với starter -EmptyDatabase/EMPTY_DATABASE, biến môi trường chỉ có hiệu lực cho lần chạy; tài khoản quản trị tạo sau đó sẽ ngăn seed tự nhập trong lần sau. Với lệnh Compose trực tiếp, dùng cấu hình env false nếu muốn luôn tắt.

Đã có bất kỳ tài khoản/khách hàng/nhãn/lô/model/audit thì seed giữ database hiện tại, không merge/upsert dữ liệu chia sẻ. Không dùng nút restore phá hủy để “nạp thêm” snapshot. Nếu muốn thử bản chia sẻ, tạo project/env/cổng mới theo [cấu hình](configuration.md).

## 4. Kiểm tra không có secret hoặc hỏng file

Với Python ≥3.12 và ./backend[dev] đã cài:

```text
python scripts/check_shared_data.py
python scripts/check-repository-secrets.py
```

Checker snapshot không nối database thật: verify file set/hash/size, bảng hợp lệ, không có sessions, actor không thể đăng nhập, ảnh gốc khớp metadata. CI cũng chạy checker. Giữ manifest gắn đúng payload; đừng chỉnh một nhãn trực tiếp trong Git rồi giữ manifest cũ. Đổi nhãn qua UI và tạo snapshot mới được review.

Checksum phát hiện lỗi/chỉnh file, không chứng minh nguồn đáng tin hay tự cấp quyền chia sẻ. Chỉ import snapshot từ repo/commit đã xác minh. Import từ chối schema revision không khớp hoặc file volume đã có nội dung khác, không ghi đè chúng.

## 5. Cập nhật snapshot bằng dữ liệu mới

Đây là thao tác **công khai**, chỉ chạy khi chủ dữ liệu đã cấp quyền. Công cụ xuất cần Python host (thư viện chuẩn) và hệ thống Docker đang chạy; dependency backend/AI dùng từ image worker. Máy sử dụng thông thường chỉ cần Docker, không cần Python host.

```text
python scripts/export_shared_data.py --confirm-public-data --output .codex-tmp/snapshot-next
```

Công cụ xác minh container/volume/network đúng Compose project, lấy DSN trong bộ nhớ (không log/ghi file), dừng backend/worker/trainer ngắn để lấy mốc nhất quán, mount kho nguồn chỉ đọc và xuất snapshot. Cuối cùng bật lại đúng container cũ, không tái tạo secret hoặc thay volume production.

Exporter loại tài khoản/phiên/audit auth/IP, lọc credential trong JSON/log lỗi, kiểm checksum ảnh/model, tạo crop bằng nhãn đã lưu, và kiểm không có session secret/mật khẩu PostgreSQL thực nằm trong payload. Quyền đọc tệp gốc mode 0600 được cấp riêng cho container xuất; ứng dụng vẫn chạy quyền thấp như trước.

Output mới phải chưa tồn tại; snapshot cũ không tự bị viết đè. Sau kiểm tra mới, đối chiếu số lượng/nhãn/hash và phạm vi công khai trước khi thay **data/snapshot duy nhất**, cập nhật manifest/tài liệu và commit/push. Không dùng git add -f để đưa .env/raw dump/private log vào Git. Các file trên 100 MiB bị exporter chặn; chuyển cơ chế LFS/release phù hợp khi dữ liệu lớn thay vì bỏ giới hạn.

## 6. Huấn luyện từ dữ liệu chia sẻ

UI đọc nhãn đã khôi phục như nhãn cũ, có thể sửa/bổ sung tiếp. Tổng 37 mẫu chưa đạt ngưỡng mặc định 200; không hạ gate kích hoạt chỉ để có mô hình active.

TSV có dạng đường_dẫn_crop<TAB>chuỗi_số, giữ 0 đầu. Tập train/validation được tạo bằng logic chia hiện hành, nhưng 37 ảnh chưa có identity công tơ đã xác minh: validation_groups_verified=false và independent_holdout=false. Không dùng 7 crop này làm chứng nhận precision 100% hoặc bật auto-confirm.

Pipeline huấn luyện hai Ridge định vị, xuất crop/benchmark pretrained; chưa tự fine-tune reader. Xem [huấn luyện](training.md). Nhãn số/vùng lưu trong database là nguồn để chỉnh tiếp, crop là dẫn xuất có thể tạo lại.

## 7. Snapshot không thay backup riêng

Sau sử dụng, nhãn/chỉ số mới nằm trong volumes của máy nhận, không tự đồng bộ lên GitHub. Backup riêng vẫn phải gồm database/storage/models cùng mốc và cấu hình secret lưu bảo mật. Xem [backup/restore](backup-restore.md). Không mặc nhiên công khai dữ liệu phát sinh chỉ vì repo đã kèm một snapshot được cho phép.
