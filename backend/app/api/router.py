from fastapi import APIRouter

from app.api.routes.audit import router as audit_router
from app.api.routes.auth import router as auth_router
from app.api.routes.batches import router as batches_router
from app.api.routes.customers import router as customers_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.evaluation import router as evaluation_router
from app.api.routes.exports import router as exports_router
from app.api.routes.health import router as health_router
from app.api.routes.images import router as images_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.models import router as models_router
from app.api.routes.results import router as results_router
from app.api.routes.settings import router as settings_router
from app.api.routes.training import router as training_router
from app.api.routes.users import router as users_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["Xác thực"])
api_router.include_router(batches_router, prefix="/batches", tags=["Lô dữ liệu"])
api_router.include_router(customers_router, prefix="/customers", tags=["Khách hàng"])
api_router.include_router(health_router, prefix="/health", tags=["Trạng thái hệ thống"])
api_router.include_router(images_router, prefix="/images", tags=["Hình ảnh"])
api_router.include_router(jobs_router, tags=["Tác vụ xử lý"])
api_router.include_router(results_router, prefix="/results", tags=["Kết quả"])
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["Bảng điều khiển"])
api_router.include_router(exports_router, prefix="/exports", tags=["Xuất dữ liệu"])
api_router.include_router(audit_router, prefix="/audit", tags=["Kiểm toán"])
api_router.include_router(settings_router, prefix="/settings", tags=["Cấu hình"])
api_router.include_router(models_router, prefix="/models", tags=["Mô hình"])
api_router.include_router(evaluation_router, prefix="/evaluation", tags=["Đánh giá"])
api_router.include_router(users_router, prefix="/users", tags=["Tài khoản"])
api_router.include_router(training_router, prefix="/training", tags=["Huấn luyện"])
