# Cấu trúc source code

Dự án dùng monorepo theo ranh giới triển khai và phân lớp rõ ràng:

```text
Elec_Man/
├── ai/                         # Worker OCR và pipeline AI độc lập
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
│   ├── components/             # Component dùng chung hoặc màn hình cũ
│   ├── features/               # Module theo nghiệp vụ mới
│   │   └── administration/     # UI, API client và type của quản trị tài khoản
│   ├── hooks/                  # React hooks dùng chung
│   ├── services/               # HTTP client và API dùng chung
│   └── types/                  # Hợp đồng dùng chung nhiều feature
├── docker/                     # Reverse proxy
├── docs/                       # Tài liệu vận hành
├── scripts/                    # Backup, restore, cài model
└── docker-compose.yml          # Cấu hình triển khai cục bộ/một máy chủ
```

Code mới nên đi theo feature ở frontend nếu chỉ thuộc một nghiệp vụ. Backend tiếp tục dùng kiến trúc phân lớp vì FastAPI, Alembic và worker cùng chia sẻ model/service. Không import component ngược vào `app/`, không đặt truy vấn database trong route và không đặt mật khẩu/token trong source code.
