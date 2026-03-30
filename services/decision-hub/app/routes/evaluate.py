"""
POST /decision/evaluate  — core decision endpoint

Called by payment-service (and any future service that needs a decision).

Contract:
  Input:  decision_type + context (transfer attributes) + correlation_id
  Output: decision_id, decision (APPROVE/REJECT/CHALLENGE), reasons[], risk_score

This endpoint writes to decision_audit regardless of outcome.
That is intentional: approved transactions are auditable too.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.engine.rule_engine import run_evaluation
from app.models import DecisionAudit, DecisionRule
from shared.correlation import get_correlation_id
from shared.logging import get_logger

router = APIRouter()
logger = get_logger("decision-hub")


class EvaluateContext(BaseModel):
    client_id: str
    amount: float
    currency: str
    country: str
    device_trust: str      # HIGH | MEDIUM | LOW
    daily_sum: float
    receiver_id: str


class EvaluateRequest(BaseModel):
    decision_type: str     # e.g. "P2P_TRANSFER"
    context: EvaluateContext
    correlation_id: str | None = None


class DecisionReason(BaseModel):
    rule_id: str
    reason_code: str
    owner: str


class DecisionResponse(BaseModel):
    decision_id: str
    allowed: bool
    decision: str          # APPROVE | REJECT | CHALLENGE
    reasons: list[DecisionReason]
    risk_score: float | None
    rules_evaluated: int
    rules_matched: int


@router.post("/decision/evaluate", response_model=DecisionResponse)
async def evaluate(request: EvaluateRequest, db: AsyncSession = Depends(get_db)):
    correlation_id = request.correlation_id or get_correlation_id()
    decision_id = uuid.uuid4()

    logger.info(
        "decision evaluation started",
        extra={
            "service": "decision-hub",
            "correlation_id": correlation_id,
            "event": "evaluation_started",
            "decision_type": request.decision_type,
            "context": request.context.model_dump(),
        },
    )

    # Load active rules ordered by priority (lower = evaluated first)
    result = await db.execute(
        select(DecisionRule)
        .where(DecisionRule.active == True)  # noqa: E712
        .order_by(DecisionRule.priority.asc())
    )
    rules = result.scalars().all()

    if not rules:
        logger.warning(
            "no active rules found",
            extra={"service": "decision-hub", "correlation_id": correlation_id, "event": "no_rules"},
        )

    ctx_dict = request.context.model_dump()
    engine_result = run_evaluation(rules, ctx_dict)

    # Write immutable audit record
    audit = DecisionAudit(
        id=uuid.uuid4(),
        decision_id=decision_id,
        transfer_context=ctx_dict,
        rules_checked=engine_result.rules_checked,
        rules_matched=engine_result.rules_matched,
        final_decision=engine_result.decision,
        risk_score=engine_result.risk_score,
        correlation_id=correlation_id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(audit)
    await db.commit()

    logger.info(
        "decision evaluation complete",
        extra={
            "service": "decision-hub",
            "correlation_id": correlation_id,
            "event": "evaluation_complete",
            "decision_id": str(decision_id),
            "decision": engine_result.decision,
            "allowed": engine_result.allowed,
            "rules_evaluated": len(engine_result.rules_checked),
            "rules_matched": len(engine_result.rules_matched),
            "risk_score": str(engine_result.risk_score) if engine_result.risk_score else None,
        },
    )

    return DecisionResponse(
        decision_id=str(decision_id),
        allowed=engine_result.allowed,
        decision=engine_result.decision,
        reasons=[DecisionReason(**r) for r in engine_result.reasons],
        risk_score=float(engine_result.risk_score) if engine_result.risk_score is not None else None,
        rules_evaluated=len(engine_result.rules_checked),
        rules_matched=len(engine_result.rules_matched),
    )
