from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.security.middleware import SecurityMiddleware


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    logger = get_logger(__name__)
    logger.info("application_starting", extra={"environment": get_settings().app_env})
    yield
    logger.info("application_stopping")


settings = get_settings()
production = settings.app_env == "production"
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None if production else "/docs",
    redoc_url=None if production else "/redoc",
    openapi_url=None if production else "/openapi.json",
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_host_list)
if settings.enforce_https:
    app.add_middleware(HTTPSRedirectMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
    expose_headers=["X-Total-Count"],
)
app.add_middleware(SecurityMiddleware)


app.include_router(api_router, prefix="/api/v1")
