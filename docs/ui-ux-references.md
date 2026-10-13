# Tham khảo UI/UX — 05/10/2026

Các mẫu dưới đây được tham khảo từ tài liệu chính thức; không sao chép mã nguồn, thương hiệu hoặc dữ liệu của bên thứ ba.

| Nguồn | Mẫu tương tác | Áp dụng trong dự án |
|---|---|---|
| [Label Studio Data Manager](https://labelstud.io/guide/manage_data) | Danh sách công việc và lọc theo trạng thái | Giữ nhóm trạng thái có số lượng, phân biệt lưu nhãn với xác nhận chính thức |
| [CVAT Interface](https://www.cvat.ai/academy/cvat-overview) | Không gian ảnh và công cụ chú thích | Thêm chế độ tập trung ẩn danh sách ảnh, không làm mất bản nháp; giữ công cụ và thông tin chỉ số bên cạnh |
| [ThingsBoard Smart Energy](https://thingsboard.io/use-cases/smart-energy/) | Thống kê năng lượng và dữ liệu theo thời gian | Thẻ số liệu thống nhất, số dễ đọc, thời điểm cập nhật, điều khiển tự làm mới, giải thích trạng thái chưa có dữ liệu |
| [MLflow Tracking](https://mlflow.org/docs/latest/ml/tracking/) | Theo dõi phiên chạy, trạng thái và chỉ số đánh giá | Làm rõ mức sẵn sàng của dữ liệu và khu vực lịch sử huấn luyện/đánh giá; không triển khai MLflow mới |

Giữ thanh điều hướng trên cùng và phân quyền ba vai trò. Người xem chỉ thấy dashboard; quản trị vận hành không thấy huấn luyện hoặc cấu hình. Phông chữ hệ thống hỗ trợ tiếng Việt, không tải font/CDN ngoài. Không thêm dependency giao diện.

Các thẻ không tương tác không được trình bày như nút. Tự cập nhật dashboard có thể tạm dừng. Thông báo lỗi sau lần tải thành công đánh dấu dữ liệu cũ; không gắn nhãn “trực tiếp” cho dữ liệu chưa kiểm chứng. Tổng tiền được trình bày là tạm tính, không thay đổi công thức tính tiền trong đợt UI này.
