# Cải tiến độ tin cậy bước nhập dữ liệu — 13/10/2026

> Bổ sung sau [bản công khai có dữ liệu](public-data-verification-2026-10-13.md). Đây là kiểm chứng bản source đã chỉnh tại workspace, không phải kết quả CI của commit đã phát hành trước đó.

## Vấn đề và sửa đổi

Trước đây seed kiểm tra toàn bộ snapshot trước khi biết database đã có dữ liệu, nhập từng hàng bằng một lệnh INSERT, và chép trực tiếp vào tệp đích. Snapshot thiếu/hỏng có thể chặn khởi động lại máy đang dùng; lỗi I/O có thể để lại tệp đích dở khiến lần thử lại từ chối checksum.

Bản cải tiến:

- Giữ khóa transaction PostgreSQL, kiểm tra database trước. Có tài khoản/nghiệp vụ thì bỏ qua snapshot; không đọc, merge hay ghi đè.
- Database mới vẫn bắt buộc snapshot hợp lệ: checksum, đúng bảng/cột, actor inactive, không có sessions và migration tương ứng.
- Nhập bằng SQLAlchemy parameterized, tối đa 200 hàng/lô, vẫn giữ thứ tự foreign key và một transaction database.
- Chép tệp vào tệp tạm cùng thư mục, kiểm hash, flush/fsync; tạo hard link đích nguyên tử và không thay tệp đã tồn tại. Tệp cùng hash được dùng lại, tệp khác bị từ chối.
- Khi lỗi stream/fsync/link được bắt, dọn đúng tệp tạm vừa tạo; không tự xóa tệp volume cũ.

## Kiểm chứng

| Phạm vi | Kết quả |
|---|---|
| Backend unit/regression | 811 passed, 2 warning deprecation TestClient/httpx |
| PostgreSQL integration đầy đủ | 29 passed, 1 warning TestClient/httpx |
| AI với source mount chỉ đọc | 37 passed |
| Frontend logic thuần | 15 passed; không sửa UI trong bước này |
| Snapshot regression trên Docker Linux | 35 passed; chạy UID 10001, filesystem chỉ đọc ngoài tmpfs, network none, cap drop ALL |
| Ruff check/format, link tài liệu, secret pattern, snapshot hashes và diff | Đạt |
| Readiness localhost | HTTP 200; không tái tạo container/credential hoặc ghi vào database nguồn |

Tổng **892 bài kiểm thử** ở bốn bộ backend/integration/AI/frontend. 35 bài snapshot chạy lại trong Docker là kiểm chứng môi trường bổ sung, không cộng trùng vào tổng.

Năm integration mới dùng schema ngẫu nhiên trong PostgreSQL thử do runner tạo, không gắn volume thật:

1. 601 khách hàng giả được nhập bằng **4 lệnh INSERT**, thay vì 601 lệnh đơn của thuật toán cũ; lần nhập sau bỏ qua cả đường dẫn snapshot không tồn tại. Đây là số lệnh, không phải tuyên bố giảm 99% thời gian toàn hệ thống.
2. Lỗi unique constraint ở lô cuối rollback toàn bộ khách hàng và giữ cấu hình mặc định. Sửa fixture rồi thử lại thành công, không thay inode tệp đã chép đúng.
3. Hai tiến trình nhập đồng thời trả đúng một thành công/một bỏ qua, không nhân đôi 601 khách hàng.
4. Migration không khớp bị từ chối trước khi chép tệp, không nhập khách hàng.
5. Snapshot công khai được khôi phục đầy đủ vào schema/thư mục thử: số hàng mọi bảng khớp; chỉ số/trạng thái/revision/hai polygon giữ nguyên; toàn bộ 133 tệp storage và 3 artifact model khớp SHA-256.

Runner dọn container/schema/thư mục thử; dữ liệu fixture có thể tạo lại. Không sửa snapshot công khai, 660 khách hàng, 61 ảnh, 37 nhãn hoặc mô hình đang dùng. Không chạy train hay mở tự xác nhận.

## Giới hạn

Database và filesystem không commit nguyên tử chung. Nếu database thất bại sau khi công bố tệp, tệp hoàn chỉnh có thể còn để lần chạy sau kiểm tra/dùng lại. Kill tiến trình/mất điện có thể để lại tệp tạm; không tự dọn tệp không biết chủ sở hữu. Hard link cần filesystem hỗ trợ; đã thử NTFS host và tmpfs Linux trong Docker, không chứng minh mọi loại NFS/cloud volume hoặc độ bền sau mất điện.

Lần này không benchmark tải OCR/train hoặc độ chính xác ảnh; không deploy Internet. CI mới chưa được chạy trên GitHub vì thay đổi này chưa commit/push. Bước AI tiếp theo vẫn là xác minh định danh/nhóm công tơ cho dữ liệu, chuẩn bị holdout độc lập, rồi mới fine-tune/đánh giá reader; không hạ gate để bỏ qua thiếu dữ liệu.
