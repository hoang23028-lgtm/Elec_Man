# Cấu trúc source code

Dự án dùng monorepo theo ranh giới triển khai và phân lớp rõ ràng:

```text
Elec_Man/
├── .github/                    # CI, CodeQL và cập nhật dependency tự động
├── ai/                         # Worker OCR, trainer và pipeline AI độc lập
│   ├── pipeline/               # Tiền xử lý, định vị và điều phối bốn tầng
│   ├── readers/                # PP-OCRv6, PARSeq và cơ chế đồng thuận
│   ├── services/               # HTTP service suy luận nội bộ
│   ├── tools/                  # CLI benchmark/chẩn đoán không chạy production
│   ├── training/               # Dataset, keypoint regressor và trainer
│   ├── model_runtime.py        # Nạp động model ACTIVE, kiểm tra checksum
│   ├── trainer.py              # Tiến trình lập lịch/khôi phục phiên train
│   └── worker.py               # Tiến trình xử lý ảnh trong hàng đợi
├── backend/
│   ├── alembic/versions/       # Migration cơ sở dữ liệu tuần tự
│   ├── app/
│   │   ├── api/routes/         # HTTP adapter, không chứa nghiệp vụ dài
│   │   ├── core/               # Cấu hình, database, logging
│   │   ├── models/             # SQLAlchemy entities
│   │   ├── schemas/            # Hợp đồng request/response Pydantic
│   │   ├── security/           # Xác thực, CSRF, mật khẩu, rate limit
│   │   └── services/           # Luật nghiệp vụ và transaction
│   └── tests/                  # Unit/API tests
├── frontend/
│   ├── app/                    # Next.js App Router, layout và global style
│   ├── components/             # Component giao diện dùng chung
│   ├── features/               # Module theo từng nghiệp vụ
│   │   ├── administration/     # UI, API client và type của quản trị tài khoản
│   │   ├── batches/            # Danh sách và chi tiết lô dữ liệu
│   │   ├── dashboard/          # Thống kê công khai
│   │   ├── model-lifecycle/    # Dataset, model và phiên huấn luyện
│   │   ├── operations/         # Upload, kiểm duyệt và kết quả xử lý
│   │   └── traceability/       # Nhật ký truy vết
│   ├── hooks/                  # React hooks dùng chung
│   ├── lib/                    # Hàm thuần, không phụ thuộc React
│   ├── services/               # HTTP client và API dùng chung
│   └── types/                  # Hợp đồng dùng chung nhiều feature
├── docker/                     # Reverse proxy
├── docs/                       # Tài liệu vận hành
├── scripts/                    # Backup, restore, kiểm tra secret và cài model
└── docker-compose.yml          # Cấu hình triển khai cục bộ/một máy chủ
```

Code frontend chỉ thuộc một nghiệp vụ phải nằm trong `features`; `components` chỉ dành cho thành phần dùng chung và `lib` dành cho hàm thuần. Backend tiếp tục dùng kiến trúc phân lớp vì FastAPI, Alembic và worker cùng chia sẻ model/service. Không import component ngược vào `app/`, không đặt truy vấn database trong route và không đặt mật khẩu/token trong source code.
