"""
POST /p2p/transfer  — TO-BE flow (via Decision Hub)

This is the correct engineering approach. Compare with transfer_legacy.py
to understand what we're moving away from.

FLOW:
  1. Require Idempotency-Key → 400 if missing
  2. Check idempotency store → if exists, return cached response (HTTP 200)
     Note: NOT 409. The client cannot distinguish a retry from a fresh call.
  3. Create transfer with status=NEW
  4. Call decision-hub → on failure: status=FAILED, return error
  5. decision=REJECT → status=REJECTED, save idempotency, return
  6. decision=APPROVE|CHALLENGE → status=DECIDED
  7. Call ledger-mock → on failure: status=FAILED, save idempotency, return
  8. status=POSTED, save idempotency, return

WHAT THIS DEMONSTRATES:
  - Status transitions are explicit and logged (NEW→REJECTED, NEW→DECIDED→POSTED)
  - Decision Hub owns "why" — payment-service only asks and acts on the answer
  - Idempotency prevents duplicate money movement on retries
  - Failure at any step results in a deterministic, queryable status
"""

import uuid
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models import PaymentIdempotency, PaymentTransfer
from app.services import decision_client, ledger_client, lifecycle
from shared.correlation import get_correlation_id
from shared.logging import get_logger

router = APIRouter()
logger = get_logger("payment-service")

# Internal pre-check threshold. Transfers exceeding this are rejected locally
# before reaching the decision hub.
_INTERNAL_DAILY_LIMIT = 9_000_000


class TransferRequest(BaseModel):
    client_id: str
    receiver_id: str
    amount: float
    currency: str
    country: str
    device_trust: str   # HIGH | MEDIUM | LOW
    daily_sum: float


def _log_transition(transfer_id: str, from_status: str, to_status: str, correlation_id: str, **extra):
    logger.info(
        f"transfer status transition: {from_status} → {to_status}",
        extra={
            "service": "payment-service",
            "correlation_id": correlation_id,
            "event": "status_transition",
            "transfer_id": transfer_id,
            "from_status": from_status,
            "to_status": to_status,
            **extra,
        },
    )


@router.post("/p2p/transfer")
async def create_transfer(
    request_body: TransferRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    # 1. Require Idempotency-Key
    idempotency_key = request.headers.get("Idempotency-Key")
    if not idempotency_key:
        correlation_id = get_correlation_id()
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "IDEMPOTENCY_KEY_MISSING",
                "message": "Idempotency-Key header is required",
                "correlation_id": correlation_id,
                "service": "payment-service",
            },
        )

    # Forward fail mode header to ledger if present
    fail_mode = request.headers.get("X-Fail-Mode")
    correlation_id = get_correlation_id()

    # 2. Create transfer record with status=NEW
    transfer_id = uuid.uuid4()
    transfer = PaymentTransfer(
        id=transfer_id,
        idempotency_key=idempotency_key,
        client_id=request_body.client_id,
        receiver_id=request_body.receiver_id,
        amount=request_body.amount,
        currency=request_body.currency,
        country=request_body.country,
        device_trust=request_body.device_trust,
        daily_sum=request_body.daily_sum,
        status="NEW",
        correlation_id=correlation_id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(transfer)
    await db.commit()

    logger.info(
        "transfer created",
        extra={
            "service": "payment-service",
            "correlation_id": correlation_id,
            "event": "transfer_created",
            "transfer_id": str(transfer_id),
            "amount": request_body.amount,
            "currency": request_body.currency,
            "country": request_body.country,
        },
    )

    # 3. Check idempotency store
    existing = await db.execute(
        select(PaymentIdempotency).where(PaymentIdempotency.idempotency_key == idempotency_key)
    )
    cached = existing.scalar_one_or_none()
    if cached:
        logger.info(
            "idempotent replay",
            extra={
                "service": "payment-service",
                "correlation_id": correlation_id,
                "event": "idempotent_replay",
                "idempotency_key": idempotency_key,
                "transfer_id": str(cached.transfer_id),
            },
        )
        return {**cached.response_snapshot, "idempotent": True}

    # Pre-check: enforce local daily limit before calling decision hub.
    # Transfers above this threshold are rejected without an audit record.
    if request_body.daily_sum + request_body.amount > _INTERNAL_DAILY_LIMIT:
        transfer.status = "REJECTED"
        transfer.updated_at = datetime.now(timezone.utc)
        await db.commit()
        _log_transition(
            str(transfer_id), "NEW", "REJECTED", correlation_id,
            reason="daily_limit_exceeded",
        )
        response_body = {
            "transfer_id": str(transfer_id),
            "status": "REJECTED",
            "idempotent": False,
            "decision": None,
            "reason": "daily_limit_exceeded",
            "correlation_id": correlation_id,
        }
        await _save_idempotency(db, idempotency_key, transfer_id, response_body)
        await db.commit()
        return response_body

    # 4. Call decision-hub
    try:
        decision = await decision_client.evaluate(
            client_id=request_body.client_id,
            receiver_id=request_body.receiver_id,
            amount=request_body.amount,
            currency=request_body.currency,
            country=request_body.country,
            device_trust=request_body.device_trust,
            daily_sum=request_body.daily_sum,
            correlation_id=correlation_id,
        )
    except (httpx.HTTPError, httpx.TimeoutException) as exc:
        # Decision hub unreachable → NEW → FAILED
        transfer.mark_failed("decision_hub_unreachable")
        await db.commit()
        _log_transition(str(transfer_id), "NEW", "FAILED", correlation_id, reason="decision_hub_unreachable", error=str(exc))

        response_body = {
            "transfer_id": str(transfer_id),
            "status": "FAILED",
            "idempotent": False,
            "error_code": "DECISION_HUB_UNAVAILABLE",
            "message": "Decision hub is unavailable. Transfer failed.",
            "correlation_id": correlation_id,
            "service": "payment-service",
        }
        await _save_idempotency(db, idempotency_key, transfer_id, response_body)
        await db.commit()
        raise HTTPException(status_code=503, detail=response_body)

    # 5. Decision = REJECT → NEW → REJECTED
    if not decision.allowed:
        transfer.status = "REJECTED"
        transfer.updated_at = datetime.now(timezone.utc)
        await db.commit()
        _log_transition(
            str(transfer_id), "NEW", "REJECTED", correlation_id,
            decision_id=decision.decision_id,
            reasons=[r.model_dump() for r in decision.reasons],
        )

        response_body = {
            "transfer_id": str(transfer_id),
            "status": "REJECTED",
            "idempotent": False,
            "decision": {
                "decision_id": decision.decision_id,
                "allowed": False,
                "decision": decision.decision,
                "reasons": [r.model_dump() for r in decision.reasons],
                "risk_score": decision.risk_score,
                "rules_evaluated": decision.rules_evaluated,
                "rules_matched": decision.rules_matched,
            },
            "correlation_id": correlation_id,
        }
        await _save_idempotency(db, idempotency_key, transfer_id, response_body)
        await db.commit()
        return response_body

    # 6. Decision = APPROVE | CHALLENGE → NEW → DECIDED
    await lifecycle.apply_decided(transfer, decision.decision_id, db)
    _log_transition(
        str(transfer_id), "NEW", "DECIDED", correlation_id,
        decision_id=decision.decision_id,
        decision=decision.decision,
    )

    # 7. Call ledger-mock
    try:
        posting = await ledger_client.post_transfer(
            transfer_id=str(transfer_id),
            amount=request_body.amount,
            currency=request_body.currency,
            correlation_id=correlation_id,
            fail_mode=fail_mode,
        )
        final_status = "POSTED"
        posting_data = {"posting_id": posting.posting_id, "status": posting.status}
    except (httpx.HTTPError, httpx.TimeoutException) as exc:
        final_status = "FAILED"
        posting_data = {"posting_id": None, "status": "FAILED", "fail_reason": str(exc)}

    # 8. Update final status → DECIDED → POSTED or DECIDED → FAILED
    prev_status = transfer.status
    transfer.status = final_status
    transfer.updated_at = datetime.now(timezone.utc)
    await db.commit()
    _log_transition(str(transfer_id), prev_status, final_status, correlation_id, posting=posting_data)

    response_body = {
        "transfer_id": str(transfer_id),
        "status": final_status,
        "idempotent": False,
        "decision": {
            "decision_id": decision.decision_id,
            "allowed": decision.allowed,
            "decision": decision.decision,
            "reasons": [r.model_dump() for r in decision.reasons],
            "risk_score": decision.risk_score,
            "rules_evaluated": decision.rules_evaluated,
            "rules_matched": decision.rules_matched,
        },
        "posting": posting_data,
        "correlation_id": correlation_id,
    }
    await _save_idempotency(db, idempotency_key, transfer_id, response_body)
    await db.commit()
    return response_body


async def _save_idempotency(db: AsyncSession, key: str, transfer_id: uuid.UUID, snapshot: dict):
    record = PaymentIdempotency(
        idempotency_key=key,
        transfer_id=transfer_id,
        response_snapshot=snapshot,
        created_at=datetime.now(timezone.utc),
    )
    db.add(record)


@router.get("/p2p/transfers/{transfer_id}")
async def get_transfer(transfer_id: str, db: AsyncSession = Depends(get_db)):
    try:
        uid = uuid.UUID(transfer_id)
    except ValueError:
        raise HTTPException(status_code=422, detail={"error_code": "INVALID_UUID"})

    result = await db.execute(select(PaymentTransfer).where(PaymentTransfer.id == uid))
    transfer = result.scalar_one_or_none()

    if not transfer:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "TRANSFER_NOT_FOUND",
                "transfer_id": transfer_id,
                "correlation_id": get_correlation_id(),
                "service": "payment-service",
            },
        )

    return {
        "transfer_id": str(transfer.id),
        "status": transfer.status,
        "client_id": transfer.client_id,
        "receiver_id": transfer.receiver_id,
        "amount": float(transfer.amount),
        "currency": transfer.currency,
        "country": transfer.country,
        "device_trust": transfer.device_trust,
        "daily_sum": float(transfer.daily_sum),
        "decision_id": str(transfer.decision_id) if transfer.decision_id else None,
        "correlation_id": transfer.correlation_id,
        "created_at": transfer.created_at.isoformat(),
        "updated_at": transfer.updated_at.isoformat(),
    }
