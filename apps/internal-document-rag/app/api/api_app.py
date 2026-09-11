import logging
import os

os.environ["ANONYMIZED_TELEMETRY"] = "False"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.middleware.logging_middleware import RequestLoggingMiddleware
from app.api.routers import (
    analytics,
    auth,
    chat,
    dashboard,
    documents,
    export,
    monitoring,
    providers,
    user_auth,
    users,
    video_processing,
    workspace,
)
from app.api.routers import settings as settings_router
from app.api.schemas.base import ErrorResponse
from app.config import settings

logger = logging.getLogger(__name__)

app = FastAPI(
    title="RAG Admin Console REST API",
    description="REST API layer powering the Internal Document RAG Admin Console",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# 1. Enable CORS for frontend web application
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Add Request Logging Middleware
app.add_middleware(RequestLoggingMiddleware)

# 3. Register Routers under /api/v1 prefix
api_v1_prefix = "/api/v1"

# --- Admin Console routers (unchanged) ---
app.include_router(auth.router, prefix=api_v1_prefix)
app.include_router(dashboard.router, prefix=api_v1_prefix)
app.include_router(analytics.router, prefix=api_v1_prefix)
app.include_router(monitoring.router, prefix=api_v1_prefix)
app.include_router(providers.router, prefix=api_v1_prefix)
app.include_router(settings_router.router, prefix=api_v1_prefix)
app.include_router(users.router, prefix=api_v1_prefix)
app.include_router(export.router, prefix=api_v1_prefix)

# --- User Portal routers (new) ---
app.include_router(user_auth.router, prefix=api_v1_prefix)
app.include_router(documents.router, prefix=api_v1_prefix)
app.include_router(chat.router, prefix=api_v1_prefix)
app.include_router(workspace.router, prefix=api_v1_prefix)
app.include_router(video_processing.router, prefix=api_v1_prefix)


# 4. Centralized Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch unhandled exceptions and return uniform error response format.
    Prevents leaking internal stack traces, API keys, or internal file paths.
    """
    logger.error(
        "Unhandled exception processing %s: %s", request.url.path, exc, exc_info=True
    )
    error_body = ErrorResponse(
        success=False,
        message="An unexpected error occurred while processing your request.",
        errors=["Internal server error"],
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_body.model_dump(),
    )


@app.get("/health", tags=["Health Check"])
def health_check():
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "environment": settings.environment,
    }
