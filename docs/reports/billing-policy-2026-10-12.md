# Phiên bản biểu giá và VAT — 12/10/2026

> Báo cáo lịch sử theo ngày, không phải hướng dẫn bản hiện hành. Xem [danh mục tài liệu](../README.md).

## Phạm vi đã triển khai

Dashboard tính tiền tham khảo theo **tháng ghi điện**, không theo ngày tải ảnh
hay ngày người kiểm duyệt xác nhận. Tổng thống kê, biểu đồ và từng dòng chi tiết
dùng cùng danh mục phiên bản trong `electricity_billing_policy.py`.
Danh mục chỉ chứa các mức giá mà dữ liệu khách hàng hiện tại có thể sử dụng;
đã bỏ các bảng cấp điện áp/ba khung giờ không được luồng tính tiền sử dụng.

| Kỳ | Biểu giá | VAT | Xử lý |
| --- | --- | --- | --- |
| 01–04/2025 | 2699/QĐ-BCT | 8%, 180/2024/NĐ-CP | Tính theo phiên bản cũ |
| 05/2025 | Đổi giá ngày 10/05 | 8% | Không tự tính toàn tháng theo một giá |
| 06/2025 | 1279/QĐ-BCT | 8%, 180/2024/NĐ-CP | Tính theo phiên bản mới |
| 07/2025–12/2026 | 1279/QĐ-BCT | 8%, 204/2025/QH15 | Theo chính sách đã xác minh |
| Từ 01/2027 | Phiên bản giá còn hiệu lực trong danh mục | Mức thông thường 10% khi kỳ giảm thuế kết thúc | Quy tắc theo văn bản hiện có, không dự báo chính sách tương lai |
| Trước 01/2025 | Có thể thiếu giá hoặc VAT đã xác minh | Không mặc định | Hiển thị lý do, không cộng vào tổng tiền |

Ngày kết thúc của phiên bản là mốc **không bao gồm**. Chỉ tháng được một phiên
bản bao phủ trọn vẹn mới được tính theo phiên bản đó. Tháng đổi giá giữa kỳ cần
bổ sung ngày chốt, chỉ số hoặc dữ liệu phân bổ trước khi tính; tính năng phân bổ
này **chưa được triển khai**. Dữ liệu đang lưu theo tháng lịch, không có chu kỳ
ghi chỉ số thực tế của nhà cung cấp điện; đây không phải công cụ lập hóa đơn EVN.

## Nguồn chính thức đối chiếu

- [EVNSPC: bảng đối chiếu 2699/QĐ-BCT và 1279/QĐ-BCT](https://www.cskh.evnspc.vn/TraCuu/ThongTinGiaDien) dùng để xác minh các mức giá của nhóm sinh hoạt, sản xuất, kinh doanh và hành chính.
- [1279/QĐ-BCT, hiệu lực 10/05/2025](https://vanban.chinhphu.vn/?classid=2&docid=213617&pageid=27160).
- [180/2024/NĐ-CP](https://vanban.chinhphu.vn/?classid=0&docid=212248&pageid=27160), [thời gian giảm VAT đầu năm 2025](https://baochinhphu.vn/giam-thue-gia-tri-gia-tang-den-30-6-2025-10225010120291057.htm).
- [204/2025/QH15](https://vanban.chinhphu.vn/default.aspx?docid=214209&pageid=27160), [giảm VAT đến hết 31/12/2026](https://xaydungchinhsach.chinhphu.vn/toan-van-nghi-quyet-so-204-2025-qh15-ve-giam-thue-gia-tri-gia-tang-119250628082120511.htm).
- [Luật Thuế GTGT 48/2024/QH15](https://vanban.chinhphu.vn/?docid=212476&pageid=27160), căn cứ mức thông thường khi không có chính sách giảm thuế.

Không xem khung giá bán lẻ bình quân hoặc thông báo đổi khung giờ là một bảng
đơn giá mới. Giá/chính sách có thể thay đổi sau lần đối chiếu này; không cam kết
các mức hiện tại sẽ tiếp tục áp dụng trong tương lai.

## Giao diện và hợp đồng API

Mỗi dòng dashboard có mã phiên bản giá, nguồn chính thức, tỷ lệ/căn cứ VAT và
`billing_note` nếu chưa tính được. Tổng tiền chỉ cộng các dòng đủ dữ liệu; một
bộ lọc chứa nhiều mức VAT không hiển thị một tỷ lệ chung gây hiểu nhầm. Giao diện
ghi rõ tổng tạm tính, không gọi là hóa đơn hay tổng thanh toán chính thức.
Skill `ui-ux-pro-max` được dùng để giữ thông báo có nội dung rõ ràng, không chỉ
dựa vào màu hoặc tooltip; không thay đổi điều hướng/phân quyền.

Xuất JSON và Excel vẫn giữ nguyên bảy trường dữ liệu khách hàng theo mẫu đã
thống nhất. Không thêm tiền/VAT/phiên bản vào báo cáo chỉ số, không viết lại file
đã xuất và không sửa dữ liệu khách hàng, ảnh hoặc nhãn thật.

## Giới hạn cần giữ rõ

- Sinh hoạt: tính một hộ, lũy tiến sáu bậc; chưa có định mức nhiều hộ/phân bổ ngày.
- Nhóm khác: tạm tính dưới 6 kV, giờ bình thường; chưa có dữ liệu đo theo ba khung giờ.
- VAT hiện tính theo tháng ghi điện để phục vụ thống kê; chưa có ngày lập hóa đơn,
  phương pháp thuế của bên bán hoặc quy trình lập/chốt hóa đơn thuế.
- Phiên bản nằm trong mã nguồn, không phải màn hình sửa biểu giá. Khi có quyết
  định mới phải bổ sung nguồn, mốc hiệu lực và kiểm thử; không thay các đơn giá cũ.
- Chưa lưu bản chụp hóa đơn đã chốt. Dashboard có thể tính lại khi chỉ số được sửa
  có nhật ký; không được dùng nó để cam kết tính bất biến của hóa đơn đã phát hành.
- Nếu có thay đổi năm 2027, phải cập nhật danh mục trước khi sử dụng kết quả năm
  đó; mức 10% hiện là mức thông thường theo quy tắc đã có, không phải xác nhận
  rằng Nhà nước sẽ không gia hạn giảm thuế.

## Kiểm thử

Đạt 736 kiểm thử backend, 22 kiểm thử tích hợp PostgreSQL riêng và 9 kiểm thử
frontend. Ruff, TypeScript và ESLint đạt. Bao gồm các biên bậc thang, tháng đổi
giá, giá/VAT cũ, kết thúc kỳ giảm VAT, mục đích không hỗ trợ, chỉ số âm/không hữu
hạn và tổng/chi tiết/biểu đồ thống nhất. Các kiểm thử ghi dữ liệu chạy trên
database/container/thư mục ảnh tạm; không dùng dữ liệu nghiệp vụ thật.

Kiểm thử không thay thế xác nhận pháp lý, kiểm thử chịu tải hay HTTPS production.

## Triển khai localhost

Build production thành công; đã cập nhật backend/frontend/worker/trainer sau khi
sao lưu `backups/audit-20261012-233800/database.dump` (185.251 byte, kiểm tra đọc
được mục lục archive; chưa diễn tập khôi phục toàn bộ). Không thêm migration;
database vẫn ở `20261012_0028`. Trang chủ, API ready và billing trả HTTP 200.
660 khách hàng và 61 ảnh được giữ nguyên. Database hiện có **0 kỳ đã xác nhận**,
nên dashboard thật chưa có dòng tiền điện; các trường hợp có dữ liệu được kiểm
thử bằng dữ liệu riêng, không chèn dữ liệu mẫu vào hệ thống thật.
