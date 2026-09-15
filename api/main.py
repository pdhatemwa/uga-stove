import logging
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from api.config import get_settings
from api.db import SessionLocal
from api.routers import admin, auth, catalog, dashboard, records, signatures

settings = get_settings()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

logger = logging.getLogger("uga_stove")

app = FastAPI(
    title=settings.app_name,
    version="0.2.0",
    docs_url=None if settings.app_env == "production" else "/docs",
    redoc_url=None,
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

field_app_directory = Path(__file__).with_name("field")

app.mount(
    "/field",
    StaticFiles(directory=field_app_directory, html=True),
    name="offline-field-client",
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))[:80]
    request.state.request_id = request_id
    started = time.perf_counter()

    response = await call_next(request)

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"

    # Camera is permitted for thumbprint or signed-form evidence.
    # GPS collection is deliberately disabled.
    response.headers["Permissions-Policy"] = "camera=(self), geolocation=()"

    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"

    logger.info(
        "request method=%s path=%s status=%s duration_ms=%.1f request_id=%s",
        request.method,
        request.url.path,
        response.status_code,
        (time.perf_counter() - started) * 1000,
        request_id,
    )

    return response


@app.get("/health/live", include_in_schema=False)
def live():
    return {"status": "ok"}


@app.get("/health/ready", include_in_schema=False)
def ready():
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))

    return {"status": "ready"}


app.include_router(auth.router, prefix="/api/v1")
app.include_router(catalog.router, prefix="/api/v1")
app.include_router(records.router, prefix="/api/v1")
app.include_router(signatures.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")