# Kiểm tra toàn vẹn chỉ số tháng — 12/10/2026

> Báo cáo lịch sử theo ngày, không phải hướng dẫn bản hiện hành. Xem [danh mục tài liệu](../README.md).

## Lỗi đã tái hiện và sửa

Hai request xác nhận hai ảnh khác nhau cho cùng khách hàng/tháng có thể cùng vượt
qua SELECT kiểm tra tồn tại. Unique constraint ngăn dữ liệu trùng nhưng request
thua trước đây trả HTTP 500. Test tích hợp dùng hai phiên đăng nhập thật, hai luồng
và barrier tại INSERT trên PostgreSQL tạm đã tái hiện chính xác lỗi này.

`save_confirmed_monthly_reading` nay rollback giao dịch và trả HTTP 409 khi vi phạm
đúng constraint `uq_confirmed_customer_month`. Lỗi toàn vẹn khác không bị che thành
xung đột nghiệp vụ. Không thay constraint, không cần migration.

Test xác minh một request thành công, một request xung đột; chỉ có một bản ghi
chính thức. Request thua vẫn ở REVIEW_REQUIRED, giữ chỉ số OCR ban đầu, chưa có
mã khách hàng chính thức và không có audit CONFIRM_RESULT đã commit.

Test luồng vận hành bổ sung xác minh sau từ chối, xuất báo cáo tháng trả 0 dòng,
JSON rỗng; bản ghi đã từ chối không tiếp tục xuất hiện trong báo cáo mới.

## Phạm vi còn lại

- Đã triển khai bản sửa xung đột tháng và chống sửa đè vào localhost.
- Đã bổ sung phiên bản bản ghi và đồng bộ frontend/backend cho stale edit;
  xem kết quả kiểm tra bên dưới.
- Chưa kiểm thử toàn diện tính nhất quán snapshot khi dashboard/export chạy đồng
  thời với mọi thao tác. Đã đối chiếu 7 trường JSON/Excel và tái hiện sửa chỉ số
  giữa các truy vấn dashboard, xem kết quả bên dưới.
- Không thay đổi dữ liệu thật, không đổi biểu giá và không xóa các file báo cáo cũ.
  File báo cáo đã tải trước khi sửa/từ chối là snapshot cũ, không tự cập nhật.

## Chống sửa đè bản ghi

Migration `20261012_0028` thêm `meter_readings.revision`, khởi tạo bản ghi hiện có
ở phiên bản 1. SQLAlchemy tăng phiên bản khi cập nhật chỉ số/nhãn/vùng và kiểm tra
phiên bản khi ghi. API danh sách trả `revision` (0 nếu chưa có MeterReading).

API lưu nhãn, lưu vùng công tơ và kiểm duyệt yêu cầu `expected_revision`. Kiểm tra
diễn ra sau khi khóa ảnh và tải lại chỉ số từ database. Request dùng phiên bản
cũ trả 412 trước khi sửa chỉ số, vùng, bản ghi tháng hoặc nhật ký xác nhận. Thiếu
phiên bản trả 422. Client cũ cần tải lại trang sau triển khai.

Giao diện giữ phiên bản cùng bản nháp. Tự cập nhật danh sách không nâng phiên bản
để âm thầm cho phép lưu bản nháp cũ. Lưu thành công cập nhật phiên bản từ response.
Khi xung đột, bản nháp được giữ; nút “Tải bản mới nhất của ảnh này” yêu cầu xác nhận
bỏ bản nháp ảnh được chọn, giữ các bản nháp khác và tải lại dữ liệu.

Kiểm thử tích hợp trên PostgreSQL tạm xác minh stale label, stale region, stale
reject, thiếu phiên bản và hai phiên đăng nhập cùng lưu một ảnh: một request 200,
một request 412, chỉ số của request thắng được giữ và phiên bản tăng đúng một lần.
Kiểm thử đồng thời hai ảnh cùng khách hàng/tháng vẫn đạt (200/409).

Kết quả: 290 test backend, 9 test tích hợp (bao gồm các kịch bản bổ sung), 9 test
frontend đạt; Ruff, ESLint, TypeScript và build frontend đạt. Đây là kiểm tra API
và logic frontend; chưa tái hiện hộp thoại xung đột bằng thao tác trên trình duyệt.

Đã sao lưu database vào `backups/audit-20261012-230445/database.dump`, kiểm tra
archive đọc được và triển khai migration `20261012_0028`. Trang chủ, API ready,
dashboard trả HTTP 200. Dữ liệu giữ 660 khách hàng, 61 ảnh, 37 nhãn; không có revision
rỗng/nhỏ hơn 1. Backend/frontend/hai reader/PostgreSQL healthy, worker/trainer chạy.

## Đối chiếu dashboard, lịch sử tháng và báo cáo

Test tích hợp mới dùng một khách hàng thử và ba kỳ tháng 01–03/2026, chỉ số gốc
100, chỉ số xác nhận 150/180/220. Kiểm tra được:

- Trước xác nhận, ảnh có kết quả OCR không vào dashboard hay báo cáo tháng.
- Điện tiêu thụ từng tháng đúng 50/30/40 kWh; lọc một tháng vẫn lấy kỳ trước từ
  lịch sử đầy đủ để tính. Tổng điện/tiền/VAT khớp các dòng chi tiết và biểu đồ.
- Sửa tháng 2 từ 180 thành 190 cập nhật tiêu thụ tháng 2 thành 40, tháng 3 thành 30.
- JSON và Excel tải từ API có cùng đúng 7 trường, cùng các giá trị và chỉ số kỳ.
- Báo cáo mới dùng chỉ số mới; file đã xuất trước sửa vẫn giữ snapshot cũ.
- Từ chối tháng 2 làm kỳ đó biến mất khỏi dashboard và báo cáo mới; tháng 3 không
  gộp tiêu thụ nhiều tháng thành một kỳ khi bị thiếu kỳ liền trước.
- Khôi phục chỉ đưa ảnh về cần xử lý; phải xác nhận lại mới tái tạo dữ liệu tháng.
- Chỉ số giảm hiển thị nhưng không tạo điện tiêu thụ âm hoặc tiền điện âm.

Đã tái hiện dashboard không nhất quán khi một request sửa chỉ số hoàn tất sau
truy vấn tổng nhưng trước truy vấn chi tiết: tổng 40 kWh, dòng chi tiết 50 kWh.
API `/dashboard/billing` nay dùng giao dịch PostgreSQL `REPEATABLE READ`, chỉ đọc,
để các truy vấn trong cùng response lấy cùng snapshot. Test xác minh response
đang tải giữ chỉ số 190; request kế tiếp thấy 200. Lịch sử tháng ở Quản trị dùng
cùng API này. JSON/Excel được sinh cùng vòng lặp từ một SELECT nên cùng snapshot.

10 test tích hợp và 290 test backend đạt, Ruff đạt. Test đồng thời trên database
tạm, không tác động dữ liệu thật. Không thêm giá mới hoặc chứng nhận biểu giá
đúng pháp lý trong bước này; phiên bản hóa biểu giá là bước kế tiếp riêng.

Đã triển khai bản đọc snapshot vào localhost sau sao lưu
`backups/audit-20261012-231518/database.dump`. Trang chủ, API ready và billing
trả 200; số lượng dữ liệu thật giữ nguyên 660 khách hàng, 61 ảnh, 37 nhãn.
