"""
payment-service — owns the transfer entity, status lifecycle, and idempotency.

What this service does NOT do:
  - Evaluate business rules (that's decision-hub's job)
  - Persist money movements (that's ledger-mock's job)
  - Route requests (that's api-gateway's job)

What this service owns:
  - The transfer entity (create, read, status transitions)
  - Idempotency guarantee (one transfer per Idempotency-Key)
  - Orchestration of the TO-BE flow: call hub → call ledger → persist result

PORT: 8001
"""

import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.db.database import engine
from app.routes.transfer import router as transfer_router
from app.routes.transfer_legacy import router as legacy_router
from shared.correlation import CorrelationMiddleware, get_correlation_id
from shared.logging import get_logger

SERVICE_NAME = os.getenv("SERVICE_NAME", "payment-service")
logger = get_logger(SERVICE_NAME)

app = FastAPI(
    title="Payment Service",
    description="Transfer lifecycle, idempotency, and orchestration",
    version="1.0.0",
)

app.add_middleware(CorrelationMiddleware, generate_if_missing=False)

app.include_router(transfer_router)
app.include_router(legacy_router)


@app.get("/health")
async def health():
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
