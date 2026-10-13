# Dữ liệu được phép công khai

Chủ dự án xác nhận ngày **13/10/2026** giữ repo PUBLIC và có quyền chia sẻ dữ liệu khách hàng, ảnh và nhãn thật. Chỉ bản snapshot này là ngoại lệ được phép đưa vào Git; sự đồng ý không tự áp dụng cho mọi dữ liệu thu thập trong tương lai.

Thư mục [snapshot](snapshot/manifest.json) chứa database nghiệp vụ dạng JSON, ảnh gốc/phái sinh, nhãn, crop train/validation và artifact mô hình. Manifest có SHA-256 từng tệp. Xem [hướng dẫn khôi phục/chia sẻ](../docs/shared-data.md).

- 660 khách hàng, 11 lô, 61 ảnh.
- 37 ảnh LABELED, 24 ảnh REJECTED, **0 chỉ số tháng đã xác nhận**.
- 37 nhãn xuất JSONL, 30 crop train và 7 crop validation.
- 1 phiên huấn luyện lịch sử, 3 artifact TESTING. Không kích hoạt lại bộ đọc HOG cũ.
- 483 audit nghiệp vụ và 123 thay đổi thủ công; audit tài khoản/đăng nhập và IP không chia sẻ.
- Khoảng 19,6 MB payload, không có container image/cache/dependency trong Git.

Không kèm tài khoản có thể đăng nhập, password/hash thật, session/CSRF token, secret môi trường, khóa TLS hoặc backup SQL thô. Bốn actor không thể đăng nhập giữ UUID để liên kết người gắn nhãn trong lịch sử; không phải tài khoản vận hành cũ. Máy nhận tự tạo quản trị và secret mới.

Tập validation có 7 ảnh và chưa có nhóm công tơ đã xác minh; không phải test độc lập hoặc chứng nhận độ chính xác. Giữ chỉ số người dùng đã lưu, bao gồm số 0 đầu và nhãn cơ khí chuyển bánh số; không dùng OCR để sửa đáp án trong lúc xuất.

**Cảnh báo:** mọi người có thể tải/fork dữ liệu này. Xóa khỏi commit mới hoặc đổi repo PRIVATE sau này không thu hồi các bản đã tải. Không coi snapshot công khai là giải pháp sao lưu dữ liệu riêng.
