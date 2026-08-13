from fastapi import FastAPI
from sqlalchemy import text
import redis

from app.core.config import settings
from app.db.session import engine
from app.api.runs import router as runs_router
from app.api.operations import router as operations_router
from app.operations_ui import router as operations_ui_router
from app.services.queue import queue_depth


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
)

app.include_router(runs_router)
app.include_router(operations_router)
app.include_router(operations_ui_router)


@app.get("/")
def root():
    return {
        "service": settings.app_name,
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "operations": "/operations",
    }


@app.get("/health/live")
def live():
    return {"status": "ok"}


@app.get("/health/ready")
def ready():
    checks = {}

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as exc:
        checks["postgres"] = (
            f"error: {type(exc).__name__}"
        )

    try:
        r = redis.Redis.from_url(settings.redis_url)
        checks["redis"] = (
            "ok"
            if r.ping()
            else "error"
        )
    except Exception as exc:
        checks["redis"] = (
            f"error: {type(exc).__name__}"
        )

    status = (
        "ok"
        if all(v == "ok" for v in checks.values())
        else "degraded"
    )

    return {
        "status": status,
        "checks": checks,
        "queue_depth": (
            queue_depth()
            if checks.get("redis") == "ok"
            else None
        ),
    }
