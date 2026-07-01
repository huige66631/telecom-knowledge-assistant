from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes_chat import router as chat_router
from app.api.routes_health import router as health_router
from app.api.routes_ingest import router as ingest_router
from app.core.exceptions import AppError
from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging


setup_logging()
settings = get_settings()
logger = get_logger(__name__)

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="MVP scaffold for a telecom/electronics enterprise knowledge assistant.",
)

app.include_router(health_router)
app.include_router(chat_router, prefix=settings.api_prefix)
app.include_router(ingest_router, prefix=settings.api_prefix)


@app.exception_handler(AppError)
async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
    logger.warning("Application error: %s", exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
            }
        },
    )


@app.exception_handler(Exception)
async def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unexpected server error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_server_error",
                "message": "An unexpected server error occurred.",
            }
        },
    )


@app.get("/", tags=["root"])
def read_root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "message": "Telecom Knowledge Assistant API is running.",
    }
