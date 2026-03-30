"""
POST /p2p/transfer-legacy  — AS-IS flow (logic inside service)

THIS IS THE ANTI-PATTERN. It exists to demonstrate what we're moving away from.

Problems with this approach (intentionally present here for demo):
  1. Decision logic is buried inside business service code
  2. No audit trail — you cannot answer "which rule matched?"
  3. No rule versioning — if AML list changes, you redeploy
  4. No explainability — reasons are free-text strings, not structured
  5. No rule ownership — who do you call when AML_COUNTRY is wrong?
  6. Logic duplication — every service re-implements the same checks
  7. Testing is hard — you cannot unit-test rules without starting the service

This is the "before" state. decision-hub is the "after" state.

Compare the response of this endpoint vs /p2p/transfer:
  Legacy:  {"status": "REJECTED", "reason": "AML_BLOCKED"}
  TO-BE:   {"status": "REJECTED", "decision": {"reasons": [{"rule_id": "AML_102",
            "reason_code": "AML_COUNTRY_BLOCKED", "owner": "compliance"}], ...}}

In the legacy version, you cannot tell:
  - Which exact rule matched
  - Who owns the rule
  - What version of the rule was active
  - What all other rules evaluated to
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models import PaymentIdempotency, PaymentTransfer
from app.services import ledger_client
from shared.correlation import get_correlation_id
from shared.logging import get_logger

router = APIRouter()
logger = get_logger("payment-service")

# AML blocked countries — hardcoded. In legacy systems, this list lives in code.
# Changing it requires a code change + deploy + CAB approval.
# Who owns this list? Nobody knows. When was it last updated? Check git blame.
_AML_BLOCKED_COUNTRIES = {"IR", "KP", "CU", "SY"}

_DAILY_LIMIT = 10_000_000
_FRAUD_AMOUNT_THRESHOLD = 200_000


class TransferRequest(BaseModel):
    client_id: str
    receiver_id: str
    amount: float
    currency: str
    country: str
    device_trust: str
    daily_sum: float


@router.post("/p2p/transfer-legacy")
async def create_transfer_legacy(
    request_body: TransferRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
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

    correlation_id = get_correlation_id()
    fail_mode = request.headers.get("X-Fail-Mode")

    # --- AS-IS DECISION LOGIC (anti-pattern) ---
    # No Decision Hub. No audit. No rule ownership. No versioning.
    # This is if-else soup that grows indefinitely and becomes unmaintainable.

    rejection_reason = None

    # Check 1: Daily limit
    if request_body.daily_sum + request_body.amount > _DAILY_LIMIT:
        rejection_reason = "LIMIT_EXCEEDED"

    # Check 2: AML country blocklist
    elif request_body.country in _AML_BLOCKED_COUNTRIES:
        rejection_reason = "AML_BLOCKED"

    # Check 3: Fraud — LOW trust + high amount
    elif request_body.device_trust == "LOW" and request_body.amount > _FRAUD_AMOUNT_THRESHOLD:
        rejection_reason = "FRAUD_SUSPECTED"

    if rejection_reason:
        # No audit record written. No rule_id. No owner. No version.
        # Business cannot answer: "What rule blocked this? Who owns it?"
        logger.info(
            "legacy transfer rejected",
            extra={
                "service": "payment-service",
                "correlation_id": correlation_id,
                "event": "legacy_transfer_rejected",
                "reason": rejection_reason,
                # NOTE: no rule_id, no owner, no version
            },
        )
        return {
            "transfer_id": None,
            "status": "REJECTED",
            "reason": rejection_reason,
            # No structured reasons. No audit_id. No rule metadata.
            # The analyst cannot trace this to a specific rule version.
            "correlation_id": correlation_id,
        }

    # Passed all checks — call ledger
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

    try:
        posting = await ledger_client.post_transfer(
            transfer_id=str(transfer_id),
            amount=request_body.amount,
            currency=request_body.currency,
            correlation_id=correlation_id,
            fail_mode=fail_mode,
        )
        transfer.status = "POSTED"
        posting_data = {"posting_id": posting.posting_id, "status": "POSTED"}
    except Exception as exc:
        transfer.status = "FAILED"
        posting_data = {"status": "FAILED", "fail_reason": str(exc)}

    transfer.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return {
        "transfer_id": str(transfer_id),
        "status": transfer.status,
        "posting": posting_data,
        # No decision field. No reasons. No audit trail.
        "correlation_id": correlation_id,
    }
