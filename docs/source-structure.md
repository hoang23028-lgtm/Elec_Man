# Tổ chức source code và quy ước

## Một checkout, một Compose

Nhánh chia sẻ chuẩn là master. Không giữ các folder bản cũ, node_modules, build frontend, dữ liệu hoặc model private trong Git. Giữ migrations và báo cáo lịch sử để truy vết; không coi chúng là source vận hành dư thừa.

```text
Elec_Man/
├── README.md                    Điểm bắt đầu, lệnh chạy và giới hạn
├── .env.example                 Cấu hình mẫu không có secret thật
├── docker-compose.yml           Triển khai local duy nhất
├── .github/workflows/           CI và CodeQL
├── backend/
│   ├── app/api/routes/          HTTP + kiểm tra quyền, không nhồi logic nghiệp vụ
│   ├── app/core/                Cấu hình, database, logging
│   ├── app/models/              SQLAlchemy models
│   ├── app/schemas/             Validate request/response
│   ├── app/security/            Argon2, session, CSRF, role, rate limit
│   ├── app/services/            Nghiệp vụ, query, kiểm duyệt, file transaction
│   ├── app/scripts/             Công cụ quản trị trong container
│   ├── alembic/versions/        Chuỗi migration; không xóa vì cần cài từ đầu
│   ├── tests/                   Unit/regression
│   └── integration_tests/       HTTP/transaction thật trên PostgreSQL tạm
├── ai/
│   ├── pipeline/               Tiền xử lý, định vị, đọc mã/chuỗi
│   ├── readers/                Client/đồng thuận hai reader
│   ├── services/               API reader chạy trong image riêng
│   ├── training/               Dataset, chia tập, trainer định vị
│   ├── tools/                  Chẩn đoán/benchmark chỉ đọc
│   ├── tests/                  Kiểm thử AI
│   └── Dockerfile*             Runtime/test/readers
├── frontend/
│   ├── app/                    Next.js entry và CSS toàn cục
│   ├── features/               Trang nghiệp vụ, auth, app shell
│   ├── components/             Thành phần dùng chung
│   ├── hooks/                  Hành vi dùng chung
│   ├── lib/                    Logic thuần
│   ├── services/               API client theo nghiệp vụ
│   ├── types/                  Kiểu dữ liệu chia sẻ
│   └── tests/                  Node tests cho logic thuần
├── docker/                     Nginx HTTP/TLS mẫu
├── scripts/                    Startup, backup/restore, kiểm thử và kiểm tra repo
├── examples/                   JSON khách hàng giả
├── data/snapshot/              Snapshot khách hàng/ảnh/nhãn/training đã được phép công khai
├── docs/                       Tài liệu hiện hành
│   └── reports/                Báo cáo theo ngày, không thay hướng dẫn hiện hành
└── design-system/              Tài liệu thiết kế, không phải bản frontend thứ hai
```

## Quy ước tên và phụ thuộc

Python module/hàm snake_case; class PascalCase. TypeScript component/type PascalCase, biến/hàm camelCase; filename TS/TSX/CSS kebab-case theo feature. CLI Python dùng tên đã ghi trong tài liệu; module dùng import phải là snake_case. Tài liệu dùng kebab-case và báo cáo thêm YYYY-MM-DD.

Không đổi tên Alembic revision/migration đã phát hành chỉ để đồng nhất hình thức. Không xóa helper đang được import, hoặc compatibility xử lý phiên hợp lệ, chỉ vì có từ legacy. Đường dẫn endpoint/DB schema là hợp đồng, phải migration và test nếu đổi.

Dùng service tách logic khỏi HTTP, schema validate ở server, parameterized SQLAlchemy, frontend API client thống nhất. Một thay đổi review phải xét cả nhãn, dữ liệu tháng, file, audit, revision và UI invalidation.

## Thành phần không đưa lên GitHub

.env*, credentials, raw database dump, backups/logs riêng, dữ liệu mới chưa được phép, .agents/.codex-tmp, venv, node_modules, .next và binary build. Snapshot trong data/ là ngoại lệ đã được chủ dự án chấp thuận và kiểm tra auth/checksum; xem [dữ liệu chia sẻ](shared-data.md). Không dùng git add -f để bỏ qua chính sách secret.

Xem [kiểm thử](testing.md), [hướng dẫn phát triển](development.md) và [danh mục tài liệu](README.md).
