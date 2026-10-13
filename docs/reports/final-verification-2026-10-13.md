# Kết quả cải tiến ngày 13/10/2026

> Báo cáo lịch sử theo ngày, không phải hướng dẫn bản hiện hành. Xem [danh mục tài liệu](../README.md).

Đây là kiểm chứng tại localhost, chưa phải xác nhận sẵn sàng go-live.

## Bản chạy và dữ liệu

Trang chủ/API ready trả HTTP 200; backend/frontend healthy; worker, trainer và
hai reader đang chạy. Migration vẫn là `20261012_0028`. Giữ nguyên 660 khách
hàng, 61 ảnh, 37 nhãn và 0 bản ghi tháng chính thức. Không sửa ảnh thật, không
tự kích hoạt mô hình, không hạ ngưỡng train 200 ảnh. `should_auto_confirm` vẫn
khóa tự xác nhận cho tới khi có chính sách kiểm định độc lập.

## Thay đổi đã áp dụng

- Phân biệt AI đề xuất, nhãn đã lưu, đã xác nhận và thay đổi chưa lưu.
- Lô dữ liệu phân biệt đang tải, đang chờ, đang xử lý; không gọi lô tải dở là OCR.
- Kỳ ghi điện/tháng báo cáo xử lý cả `input` và `change`. Đã sửa trường hợp tháng
  hiện trên màn hình nhưng chưa cập nhật bản nháp. Nút tải bản mới khi xung đột
  không xuất hiện nếu cả hai ID ảnh đều rỗng.
- Tách nhóm AI liên kết UUID khách hàng, mã khách hàng và hash ảnh; bí danh có
  liên kết không bị chia sang hai tập. Thiếu định danh chỉ dùng cho chẩn đoán.
  Bộ phát triển hiện tại luôn ghi `independent_holdout=false`.
- Kích hoạt cần metadata nhóm đã định danh, ít nhất 30 ảnh validation và điểm
  vùng hợp lệ tối thiểu 0,8. NaN/Infinity/boolean/chuỗi/điểm ngoài khoảng bị chặn.
  Điểm từ sai số tọa độ không phải xác suất đọc đúng; số đo HOG cũ không được
  gán cho mô hình định vị. Metadata do quản trị khai báo không phải chứng nhận
  kiểm định độc lập; nhãn sai định danh vẫn cần con người rà soát.
- Khóa giao dịch PostgreSQL tuần tự hóa kích hoạt, không để hai mô hình cùng
  loại cùng ACTIVE. Kiểm thử hai yêu cầu train cũng chỉ tạo một phiên.
- Ẩn tham số SQL khỏi lỗi database. Quét bí mật cả source mới chưa commit.
- Backup/restore dùng đúng project/volume, bắt lỗi sao chép/giải nén và checksum
  thiếu/trùng/sai đường dẫn. Thay schema/nhập SQL dùng chung transaction với
  `ON_ERROR_STOP`; database và hai kho tệp không phải transaction chung, vẫn
  cần backup trước restore thật.
- Thêm job tích hợp PostgreSQL vào CI; cú pháp đã kiểm tra, chưa chạy GitHub
  Actions trên commit phát hành vì chưa push.

## Kiểm thử

Backend **764 đạt**, AI **37 đạt**, frontend **15 đạt**, tích hợp PostgreSQL
**24 đạt**. Bao gồm ba vai trò, CSRF, thu hồi/hết hạn phiên, upload/lưu nhãn,
xác nhận tháng/sửa có log/xuất JSON-Excel/từ chối-khôi phục, giá/VAT, revision
và thao tác đồng thời. Ruff, ESLint, TypeScript, production build đạt. Còn cảnh
báo deprecation TestClient/httpx, không làm bộ kiểm thử thất bại.

### Giao diện

Đã mở Vận hành, Các lô dữ liệu (cả trang 2), Khách hàng, Chỉ số tháng, Huấn luyện,
Kho mô hình trên tài khoản thật theo chế độ chỉ đọc. Không coi mở trang là đã
kiểm thử mọi nút.

Trong bản sao có 15 ảnh/khách hàng giả và tài khoản ADMIN:

- Menu chỉ có Tổng quan, Vận hành, Các lô dữ liệu, Quản trị.
- Lưu nhãn `00123` chưa có mã khách hàng; tải lại vẫn còn số/vùng khoanh.
- Xác nhận `TEST.001`, kỳ `2026-10`, rồi sửa `00123 → 00124` thành công. Log có
  trước/sau; database chính thức lưu 124.
- Xuất tháng 9/2026 được 0 khách hàng; tháng 10 được 1, có link Excel/JSON.
- Lần kiểm tra đầu **chưa hoàn tất UI từ chối/khôi phục**: hộp thoại `window.confirm` làm phiên
  điều khiển in-app browser kẹt. Đọc dialog/đóng tab không giải quyết được.
  Không suy diễn đã từ chối thành công. API đã qua nhưng UI cần kiểm tra tiếp
  sau khi người dùng đóng hộp thoại/tab thử `http://127.0.0.1:60534`.

Môi trường thử tự dọn container/database/kho ảnh khi hết hạn, không dùng volume
hay credential thật. Không cần đóng tab `http://localhost/` của người dùng.

### Hoàn tất kiểm tra giao diện còn lại (13:07, 13/10/2026)

Tiếp tục bằng một database mới với 15 ảnh/15 khách hàng giả. Đã cập nhật riêng
frontend tại localhost, không chạy migration hay khởi động lại backend,
worker hoặc trainer. Kiểm tra lại: 660 khách hàng, 61 ảnh, 37 nhãn, 24 ảnh từ
chối và 0 bản ghi tháng chính thức; trang chủ và API ready trả HTTP 200.

- Thay `window.confirm` của từ chối/tải lại ảnh bằng `<dialog>` không chặn
  luồng JavaScript. Hiển thị tên ảnh và ảnh hưởng tới dữ liệu chính thức,
  mặc định tập trung nút Hủy. Tab/Shift+Tab không rời hộp thoại; Escape hủy
  và trả tiêu điểm về nút gọi. Yêu cầu lặp và đóng component không tự phê duyệt.
- UI: lưu nhãn `00123` không có mã khách hàng; xác nhận `TEST.001`, tháng
  10/2026; từ chối ảnh đã xác nhận khiến báo cáo tháng còn 0 khách hàng.
  Khôi phục trở về nhóm đã gắn nhãn, vẫn giữ số và vùng khoanh.
- Báo cáo trong cùng tab bị xóa liên kết tải cũ sau thao tác xác nhận/sửa/
  từ chối/khôi phục; yêu cầu tạo lại. Phản hồi xuất đang chạy đã bị vô hiệu
  hóa không được hiển thị thành báo cáo mới. Đây không phải đồng bộ liên tab
  hoặc thu hồi các file đã được tải về trước đó.
- Hai tab thử cùng sửa một ảnh: tab thứ hai lưu `00124`; tab đầu lưu `00125`
  bị chặn do revision cũ. Hủy tải lại giữ `00125`; chấp nhận tải lại nhận
  đúng `00124`. Không ghi đè âm thầm nhãn đã lưu.
- ADMIN chỉ thấy bốn mục nghiệp vụ. SUPER_ADMIN có tài khoản, mô hình,
  cấu hình và truy vết. Khóa tài khoản giả viewer thành công; nhật ký
  hiển thị hoạt động `Có → Không`. Không đổi credential tài khoản thật.
- Cấu hình thử: lưu số mẫu 199 rồi hoàn nguyên 200; dưới mức 3 bị form chặn.
  200 là giá trị khuyến nghị/mặc định, không phải giới hạn cứng của cấu hình.
  Các trường lấy từ môi trường triển khai vẫn chỉ đọc.
- Chọn trang 2 ảnh hiển thị STT 13–15; trang 2 truy vết hiển thị STT 11–20.
  Đổi nhãn tóm tắt thành “thay đổi dữ liệu” để không gọi thay đổi worker là
  “thủ công”; bổ sung tên tiếng Việt cho các trường chẩn đoán mới.
- Kiểm tra sáu trang ở viewport 375×812 và 812×375: chiều ngang document
  không vượt client width. Bảng vẫn cuộn ngang bên trong vùng riêng.
  Sửa tiêu đề/nút thêm khách hàng trên màn hình nhỏ và bố trí bộ lọc ảnh
  gọn hơn. Hộp thoại ở 375px nằm trong viewport, không bị cắt.

840 kiểm thử tự động đạt (764 backend + 24 PostgreSQL + 37 AI + 15 frontend).
TypeScript, ESLint, production build, kiểm tra diff và quét token đạt.
Skill `ui-ux-pro-max` được dùng cho tiêu điểm bàn phím và bố cục nhãn nhỏ.
Đây không phải kiểm tra toàn bộ WCAG, mọi kích thước, hay mọi thao tác có mật
khẩu/xóa tài khoản/kích hoạt mô hình. Chỉ các luồng nêu trên được thử bằng UI.

Các tab thử mới đã đóng. Container/database/volume Docker thử của phiên này
và một phiên thử cũ đã được dọn theo tên/nhãn sở hữu; không dọn volume thật.
Không thay đổi mô hình, trọng số hoặc nhãn thực tế trong lần cập nhật này.

### HTTPS và tải ngắn

Sandbox dùng cấu hình production ở loopback, chứng chỉ thử một ngày và SSL
context tin đúng chứng chỉ. Không dùng `verify=False`, không cài chứng chỉ OS,
không vượt cảnh báo trình duyệt. HTTP chuyển HTTPS, HSTS/headers, cookie
Secure/HttpOnly/SameSite=strict/hạn 8 giờ, CORS, CSRF, vai trò, logout đều đạt.
Đăng nhập sai 5 lần trả 401, lần 6 trả 429.

- 5 upload đồng thời: tất cả thành công; p95 472 ms.
- 120 lượt đọc với 10 luồng: tất cả thành công; p95 548 ms.

Đây là tải ngắn trên 15 ảnh/15 khách hàng giả, không phải SLA, tải dài hoặc tải
phối hợp OCR/train/upload. OCR dùng fixture ở đầu ra worker.

## Chẩn đoán 37 ảnh đã gắn nhãn

`ai/tools/verify_saved_labels.py` kiểm tra hash/đường dẫn, chỉ đọc database,
không sửa nhãn, kết quả OCR lưu trữ, phiên train hoặc mô hình.

| Phạm vi | Đúng toàn chuỗi | Có trả kết quả | Kết quả sai | p50 / p95 |
| --- | ---: | ---: | ---: | ---: |
| Tự định vị toàn luồng | 10/37 (27,0%) | 12/37 | 2 | 6,51 / 9,96 giây |
| Reader với vùng và số chữ số đúng | 25/37 (67,6%) | 27/37 | 2 | 0,48 / 1,80 giây |

Chưa nạp mô hình định vị đã huấn luyện; cả 37 ảnh thiếu định danh để kiểm chứng
tách nhóm. Đây là tập phát triển gồm cả ảnh từng dùng tối ưu, không phải holdout.
Nhánh thủ công có cả vùng và số chữ số, hai nhánh không nhận đầu vào tương đương.
Thời gian nhánh thủ công chỉ đo reader trên crop, không đo toàn API/hàng đợi.

Định vị là điểm yếu lớn, nhưng reader vẫn sai ngay cả với vùng thủ công. Không
cam kết thêm đủ 200 ảnh là hoàn thành. Pipeline hiện học vùng/benchmark reader
pretrained, **chưa fine-tune trọng số PP-OCR/PARSeq bằng dữ liệu dự án**.

## Diễn tập khôi phục

Bản đầy đủ `backups/20261013T045240Z/` tạo khi tạm dừng ba dịch vụ ghi rồi bật lại.
SQL và hai archive khớp SHA-256. `scripts/rehearse_backup.py` phục hồi vào
PostgreSQL network `none`, không mở cổng, kho tệp vào thư mục tạm mới:

- 660 khách hàng, 61 ảnh, 37 nhãn, 0 bản ghi tháng, migration `20261012_0028`.
- 133 tệp lưu trữ (17.307.401 byte), 3 tệp mô hình (121.662 byte).
- Hash từng tệp khớp archive, tài nguyên diễn tập đã dọn; không phục hồi đè thật.

Dump trước cập nhật cuối `backups/audit-20261013-121909/database.dump` đã kiểm
tra danh mục, không nhầm với diễn tập đầy đủ của bản trên.

## Còn lại trước go-live

1. Đã hoàn tất các luồng UI từ chối/khôi phục, xung đột phiên bản, responsive,
   khóa tài khoản và cấu hình nêu trên. Còn mở rộng kiểm thử UI cho các thao
   tác chưa thử (credential, xóa tài khoản, nhập tệp và kích hoạt mô hình đủ
   điều kiện) bằng dữ liệu giả, không thực hiện trên tài khoản/mô hình thật.
2. Bổ sung định danh, data đa công tơ/điều kiện và holdout chưa dùng tối ưu;
   huấn luyện định vị tốt hơn, fine-tune reader và đánh giá toàn luồng trước
   khi mở tự xác nhận.
3. Tải dài và tải phối hợp trên phần cứng triển khai.
4. VPS/domain/chứng chỉ công khai, quản lý secret và host/origin production.
   TLS cục bộ không đồng nghĩa đã triển khai Internet.
5. Lịch backup, mã hóa/chuyển ngoài máy, cảnh báo lỗi/ổ đĩa/hàng đợi và người
   nhận cảnh báo. Backup cùng máy chưa đạt 3-2-1.
6. Review dữ liệu hiển thị công khai, chạy CI trên đúng commit phát hành.
