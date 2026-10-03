# Benchmark bộ đọc chuỗi hiện đại — 2026-10-01

## Kết luận

PP-OCRv6 small và PARSeq-tiny đều đọc đúng 5/7 vùng chỉ số đã gắn nhãn, trong khi mô hình HOG thử nghiệm trước đó đạt 0/7 chuỗi đúng. Hai model hiện đã thay thế HOG trong pipeline vận hành theo chế độ đồng thuận an toàn. Tập xác nhận chỉ có 7 mẫu, không phải holdout độc lập, nên confidence vẫn bị giới hạn dưới ngưỡng tự xác nhận và kết quả phải qua Human Review.

Nếu ghép theo quy tắc an toàn “chỉ chấp nhận khi hai model cùng trả về một chuỗi”, cả hai đồng thuận đúng trên 5/5 trường hợp và chuyển 2/7 trường hợp còn lại sang kiểm duyệt. Đây là ứng viên tốt nhất cho shadow mode sau khi có tập test độc lập lớn hơn.

## Kết quả thực đo trên CPU

| Bộ đọc | Đúng tuyệt đối | Coverage | Chính xác khi có kết quả | CER | P50 | P95 | Khởi tạo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| PP-OCRv6 small rec | 5/7 (71,4%) | 71,4% | 100% | 28,6% | 43,90 ms | 291,30 ms | 6.495 ms |
| PARSeq-tiny | 5/7 (71,4%) | 85,7% | 83,3% | 17,1% | 31,95 ms | 35,82 ms | 7.262 ms |
| Đồng thuận PP + PARSeq | 5/7 (71,4%) | 71,4% | 100% | — | — | — | — |

CER của trường hợp từ chối được tính như chuỗi rỗng. Thời gian nhận dạng không gồm đọc ảnh, hiệu chỉnh phối cảnh và thời gian khởi tạo model. Lần gọi đầu của PP-OCRv6 có warm-up rõ rệt; vì tập rất nhỏ, P95 chưa ổn định.

## Giao thức có thể tái lập

- Chỉ lấy bản ghi `LABELED`/`CONFIRMED` có người xác nhận cả kết quả và đa giác vùng chỉ số.
- Kiểm tra SHA-256 của file trước khi đọc; chia tập xác định theo đồng hồ bằng logic huấn luyện hiện tại.
- Hiệu chỉnh phối cảnh theo 4 điểm, bỏ bánh xe thập phân màu đỏ, không gửi ảnh ra dịch vụ cloud.
- Chỉ chấp nhận chuỗi 4–9 chữ số; không sửa đoán ký tự như `O` thành `0`.
- Benchmark chỉ đọc database và volume ảnh; báo cáo dùng SHA-256, không chứa mã khách hàng hay đường dẫn.
- Image benchmark tách khỏi worker production. Model tải vào cache tách biệt trước, sau đó benchmark chạy trong mạng dữ liệu `internal`.

Báo cáo máy đọc được nằm trong `logs/benchmarks/ppocr-v6-small-20261001.json` và `logs/benchmarks/parseq-tiny-20261001.json` (thư mục log không được Git theo dõi).

## Kiến trúc đề xuất

1. Định vị mặt công tơ.
2. Tìm bốn góc vùng bộ số và hiệu chỉnh phối cảnh.
3. Tiền xử lý nhẹ, giữ cả ảnh màu và ảnh chuẩn hóa.
4. Chạy PP-OCRv6 small và PARSeq-tiny theo batch.
5. Tự xác nhận chỉ khi hai chuỗi đồng thuận, qua kiểm tra định dạng và không vi phạm quy tắc tăng chỉ số theo tháng; các trường hợp khác vào kiểm duyệt.
6. Chỉ hiệu chỉnh confidence bằng tập validation độc lập; không dùng trực tiếp `rec_score` như xác suất đúng.

Hướng này khớp với UFPR-AMR (định vị vùng bộ đếm rồi nhận dạng) và mở rộng Copel-AMR (tìm góc, hiệu chỉnh, phát hiện ảnh không đọc được). Với dữ liệu hiện tại, nút thắt tiếp theo là tầng định vị/hiệu chỉnh và thiếu holdout, không còn là lý do để tiếp tục tối ưu bộ phân loại HOG từng ô.

## Điều kiện trước khi đưa production

- Tạo test set độc lập, không trùng ảnh/đồng hồ với train; mục tiêu trước mắt ít nhất 200 ảnh và tiếp tục thu thập hướng tới quy mô 2.000 ảnh như UFPR-AMR.
- Báo cáo exact-match, CER, coverage, precision khi tự xác nhận, P50/P95 và kết quả theo loại công tơ/độ mờ/góc chụp.
- Chỉ tự xác nhận sau khi precision trên tập độc lập đạt ngưỡng vận hành; ưu tiên tăng tỷ lệ chuyển kiểm duyệt thay vì đoán sai.
- Giữ kiểm duyệt bắt buộc cho tới khi tập độc lập đủ lớn để hiệu chỉnh confidence; không ghi đè kết quả đã xác nhận.

## Nguồn chính

- PaddleOCR 3.7.0: https://github.com/PaddlePaddle/PaddleOCR/releases/tag/v3.7.0
- PP-OCRv6: https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/algorithm/PP-OCRv6/PP-OCRv6.en.md
- PARSeq: https://github.com/baudm/parseq
- UFPR-AMR: https://arxiv.org/abs/1902.09600
- Copel-AMR: https://arxiv.org/abs/2009.10181
