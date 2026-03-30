"""
decision-hub — owns all decision logic, rule evaluation, and audit trail.

WHY this service exists:
  In a typical bank, "why was this transaction rejected?" has no single
  answer. Logic lives in 5 services, 3 BPM workflows, and Vasya's head.

  Decision Hub centralizes this: one service, one audit table, one API.
  Every decision is traceable, explainable, and reproducible.

PORT: 8002
"""

import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.db.database import engine
from app.routes.admin import router as admin_router
from app.routes.evaluate import router as evaluate_router
from shared.correlation import CorrelationMiddleware, get_correlation_id
from shared.logging import get_logger

SERVICE_NAME = os.getenv("SERVICE_NAME", "decision-hub")
logger = get_logger(SERVICE_NAME)

app = FastAPI(
    title="Decision Hub",
    description="Central decision engine — rules as data, decisions as audit trail",
    version="1.0.0",
)

app.add_middleware(CorrelationMiddleware, generate_if_missing=True)

app.include_router(evaluate_router)
app.include_router(admin_router)


@app.get("/health")
async def health():
    # Quick DB connectivity check
    try:
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "unavailable"

    return {"status": "ok", "service": SERVICE_NAME, "db": db_status}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    correlation_id = get_correlation_id()
    logger.error(
        "unhandled exception",
        extra={
            "service": SERVICE_NAME,
            "correlation_id": correlation_id,
            "event": "unhandled_exception",
            "error": str(exc),
            "path": request.url.path,
        },
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error_code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "correlation_id": correlation_id,
            "service": SERVICE_NAME,
        },
    )
