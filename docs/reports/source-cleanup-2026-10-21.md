# Dọn source, giữ triển khai hiện hành — 21/10/2026

Thực hiện sau bản tối ưu `0bc2cf5`. CI/build và CodeQL của bản đó đã đạt; không sử dụng chúng làm kết quả cho bản dọn mới.

## Đã loại bỏ

- Khả năng huấn luyện MobileNetV3 v1 và các nhánh loss/chọn epoch dành riêng cho v1. Trainer chỉ còn v2 320 px/5×5/IoU; smoke không tạo lại model v1.
- Ảnh adaptive-threshold thứ ba vốn được tạo rồi bỏ trong mọi lượt OCR khách hàng. Hai ảnh còn dùng giữ nguyên thuật toán/pixel; giới hạn bốn lượt/3 giây không đổi.
- Hai lần giải mã lại JSON request để lấy số chữ số; dùng trực tiếp tham số đã kiểm tra, vẫn xác minh response đúng độ dài.
- Lệnh tạo thư mục report lặp, import nằm trong vòng lặp và chặn timeout thừa so với ngân sách đã validate.
- Tên biến CSRF “legacy” gây hiểu nhầm: đổi thành nhánh token đăng nhập, không bỏ kiểm tra token hoặc phục hồi phiên.
- Image hai reader chỉ copy module cần cho dịch vụ; không đưa client đồng thuận của worker vào reader. Đổi client worker không còn làm mất cache build của reader vì copy cả thư mục.

## Cố ý giữ

- Đọc metadata artifact cũ để không làm mất khả năng xem/truy vết dữ liệu. Không có nhánh huấn luyện cũ.
- Ridge làm đối chứng và hai reader làm đồng thuận; encoder Torch mặc định, ONNX chỉ đối chứng. Đây là chức năng còn được dùng, không phải source trùng.
- Migrations, docs/reports lịch sử, snapshot công khai đã được phép, ảnh/nhãn, model đã lưu và backup. Không rewrite lịch sử Git, không xóa dữ liệu hoặc kích hoạt model.
- Thư viện/cache runtime cần để build; không nhầm môi trường phụ thuộc với bản source cũ. Không xóa .agents hoặc các báo cáo riêng.

Repo không có thư mục chứa bản ứng dụng cũ đang được Git theo dõi; chỉ một checkout và một Compose. Thư mục training/ cấp gốc trống và không được theo dõi, không phải trainer thứ hai. Môi trường chặn thao tác xóa thư mục này nên giữ nguyên, không tìm cách vượt chặn. Code trainer nằm ở ai/training/.

## Kiểm chứng

Thêm regression cấm huấn luyện kiến trúc cũ, không tính ảnh tiền xử lý dư và chỉ parse hai response JSON. Chạy lại đúng source mới: **871 backend + 33 PostgreSQL riêng + 69 AI trong image vừa build + 19 frontend = 992 test đạt**. Ruff/check format, snapshot/secret/docs và diff whitespace đạt. Frontend không đổi mã từ bản tối ưu trước; CI của commit mới vẫn phải build lại toàn bộ. Smoke offline, cập nhật localhost có backup và kiểm tra hai reader thật thực hiện trên image vừa build. CI/CodeQL chỉ được coi là đạt sau kết quả gắn đúng commit mới trên GitHub.

Giới hạn AI không đổi: v2 có IoU vùng số validation 58,2% trên 6 ảnh phát triển, chưa có holdout độc lập; 0 ACTIVE, tự xác nhận vẫn khóa. “Mới nhất” không đồng nghĩa đã đạt accuracy sản xuất.
