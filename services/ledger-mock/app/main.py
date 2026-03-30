"""
ledger-mock — simulates the core banking ledger (posting engine).

WHY this mock exists:
  In a real bank, the ledger is the sacred system of record. It accepts
  a posting instruction and either commits the debit/credit atomically
  or rejects it. It does not orchestrate — it just posts.

  This mock simulates three failure modes for demo purposes:
    TIMEOUT → slow ledger (common in legacy core banking systems)
    ERROR   → ledger unavailable (DB issue, maintenance, etc.)
    normal  → successful posting

  The X-Fail-Mode header is passed through api-gateway → payment-service
  → ledger-mock, demonstrating header propagation across the chain.

IDEMPOTENCY: same transfer_id → return existing posting (no duplicate debit).
This is critical: payment-service may retry on timeout, and the ledger
must not double-post.

PORT: 8003
"""

import asyncio
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import engine, get_db
from app.models import LedgerPosting
from shared.correlation import CorrelationMiddleware, get_correlation_id
from shared.logging import get_logger

SERVICE_NAME = os.getenv("SERVICE_NAME", "ledger-mock")
logger = get_logger(SERVICE_NAME)

app = FastAPI(title="Ledger Mock", version="1.0.0")
app.add_middleware(CorrelationMiddleware, generate_if_missing=True)

router = APIRouter()


class PostingRequest(BaseModel):
    transfer_id: str
    amount: float
    currency: str
    correlation_id: str


@router.post("/ledger/posting")
async def create_posting(
    body: PostingRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_fail_mode: str | None = Header(default=None, alias="X-Fail-Mode"),
):
    correlation_id = get_correlation_id() or body.correlation_id

    try:
        transfer_uuid = uuid.UUID(body.transfer_id)
    except ValueError:
        raise HTTPException(status_code=422, detail={"error_code": "INVALID_TRANSFER_ID"})

    # Idempotency: return existing posting for this transfer_id
    result = await db.execute(
        select(LedgerPosting).where(LedgerPosting.transfer_id == transfer_uuid)
    )
    existing = result.scalar_one_or_none()
    if existing:
        logger.info(
            "duplicate posting suppressed",
            extra={
                "service": SERVICE_NAME,
                "correlation_id": correlation_id,
                "event": "duplicate_posting_suppressed",
                "transfer_id": body.transfer_id,
                "posting_id": str(existing.id),
            },
        )
        return {
            "posting_id": str(existing.id),
            "status": existing.status,
            "fail_reason": existing.fail_reason,
        }

    # Simulate failure modes
    if x_fail_mode == "TIMEOUT":
        logger.info(
            "simulating ledger timeout",
            extra={"service": SERVICE_NAME, "correlation_id": correlation_id, "event": "fail_mode_timeout"},
        )
        await asyncio.sleep(5)
        # After sleeping, succeed (mimics a slow but functioning ledger)

    elif x_fail_mode == "ERROR":
        logger.warning(
            "simulating ledger error",
            extra={"service": SERVICE_NAME, "correlation_id": correlation_id, "event": "fail_mode_error"},
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "LEDGER_UNAVAILABLE",
                "message": "ledger_unavailable",
                "correlation_id": correlation_id,
                "service": SERVICE_NAME,
            },
        )

    # Normal posting
    posting = LedgerPosting(
        id=uuid.uuid4(),
        transfer_id=transfer_uuid,
        amount=body.amount,
        status="POSTED",
        fail_reason=None,
        correlation_id=correlation_id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(posting)
    await db.commit()

    logger.info(
        "posting created",
        extra={
            "service": SERVICE_NAME,
            "correlation_id": correlation_id,
            "event": "posting_created",
            "posting_id": str(posting.id),
            "transfer_id": body.transfer_id,
            "amount": body.amount,
        },
    )

    return {"posting_id": str(posting.id), "status": "POSTED", "fail_reason": None}


@router.get("/health")
async def health():
    try:
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "unavailable"
    return {"status": "ok", "service": SERVICE_NAME, "db": db_status}


app.include_router(router)


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
        },
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error_code": "INTERNAL_ERROR",
            "message": str(exc),
            "correlation_id": correlation_id,
            "service": SERVICE_NAME,
        },
    )
