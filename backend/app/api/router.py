from fastapi import APIRouter
from app.api.routes.health import router as health_router
from app.api.routes.auth import router as auth_router
from app.api.routes.batches import router as batches_router
from app.api.routes.images import router as images_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.results import router as results_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.exports import router as exports_router
api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(batches_router, prefix="/batches", tags=["batches"])
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(images_router, prefix="/images", tags=["images"])
api_router.include_router(jobs_router, tags=["jobs"])
api_router.include_router(results_router, prefix="/results", tags=["results"])
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(exports_router, prefix="/exports", tags=["exports"])
