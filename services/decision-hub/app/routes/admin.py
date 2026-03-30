"""
Admin routes for decision-hub:

  GET  /decision/rules                — list all rules (versioned catalog)
  PATCH /decision/rules/{rule_id}     — mutate a rule without redeployment
  GET  /decision/audit/{decision_id}  — full audit record for a decision

WHY PATCH without redeployment:
  In a typical bank, changing a limit threshold requires:
    1. BA writes a change request
    2. Dev codes the change
    3. QA tests
    4. CAB approves release
    5. Deploy on Saturday night

  With rules-as-data, step 1 → PATCH in 10 seconds.
  The change is: versioned (updated_at), attributable (who called the API),
  and immediately effective — without touching any code.

  DEMO: This endpoint is the "change rule without release" scenario.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models import DecisionAudit, DecisionRule
from shared.correlation import get_correlation_id
from shared.logging import get_logger

router = APIRouter()
logger = get_logger("decision-hub")


class RulePatch(BaseModel):
    active: bool | None = None
    condition_params: dict | None = None
    # Extend as needed: action, priority, etc.


class RuleResponse(BaseModel):
    rule_id: str
    version: str
    priority: int
    active: bool
    condition_type: str
    condition_params: dict
    action: str
    reason_code: str
    owner: str
    updated_at: datetime


class AuditResponse(BaseModel):
    id: str
    decision_id: str
    transfer_context: dict
    rules_checked: list
    rules_matched: list
    final_decision: str
    risk_score: float | None
    correlation_id: str | None
    created_at: datetime


@router.get("/decision/rules", response_model=list[RuleResponse])
async def list_rules(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DecisionRule).order_by(DecisionRule.priority.asc()))
    rules = result.scalars().all()
    return [
        RuleResponse(
            rule_id=r.rule_id,
            version=r.version,
            priority=r.priority,
            active=r.active,
            condition_type=r.condition_type,
            condition_params=r.condition_params,
            action=r.action,
            reason_code=r.reason_code,
            owner=r.owner,
            updated_at=r.updated_at,
        )
        for r in rules
    ]


@router.patch("/decision/rules/{rule_id}", response_model=RuleResponse)
async def patch_rule(rule_id: str, patch: RulePatch, db: AsyncSession = Depends(get_db)):
    correlation_id = get_correlation_id()

    result = await db.execute(select(DecisionRule).where(DecisionRule.rule_id == rule_id))
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(status_code=404, detail={"error_code": "RULE_NOT_FOUND", "rule_id": rule_id})

    changed_fields: dict = {}

    if patch.active is not None:
        changed_fields["active"] = {"from": rule.active, "to": patch.active}
        rule.active = patch.active

    if patch.condition_params is not None:
        changed_fields["condition_params"] = {"from": rule.condition_params, "to": patch.condition_params}
        rule.condition_params = patch.condition_params

    if not changed_fields:
        raise HTTPException(status_code=422, detail={"error_code": "NO_CHANGES", "message": "Nothing to update"})

    rule.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(rule)

    logger.info(
        "rule updated",
        extra={
            "service": "decision-hub",
            "correlation_id": correlation_id,
            "event": "rule_updated",
            "rule_id": rule_id,
            "changed_fields": changed_fields,
        },
    )

    return RuleResponse(
        rule_id=rule.rule_id,
        version=rule.version,
        priority=rule.priority,
        active=rule.active,
        condition_type=rule.condition_type,
        condition_params=rule.condition_params,
        action=rule.action,
        reason_code=rule.reason_code,
        owner=rule.owner,
        updated_at=rule.updated_at,
    )


@router.get("/decision/audit/{decision_id}", response_model=AuditResponse)
async def get_audit(decision_id: str, db: AsyncSession = Depends(get_db)):
    from uuid import UUID
    try:
        uid = UUID(decision_id)
    except ValueError:
        raise HTTPException(status_code=422, detail={"error_code": "INVALID_UUID", "field": "decision_id"})

    result = await db.execute(
        select(DecisionAudit).where(DecisionAudit.decision_id == uid)
    )
    audit = result.scalar_one_or_none()

    if not audit:
        raise HTTPException(
            status_code=404,
            detail={"error_code": "AUDIT_NOT_FOUND", "decision_id": decision_id},
        )

    return AuditResponse(
        id=str(audit.id),
        decision_id=str(audit.decision_id),
        transfer_context=audit.transfer_context,
        rules_checked=audit.rules_checked,
        rules_matched=audit.rules_matched,
        final_decision=audit.final_decision,
        risk_score=float(audit.risk_score) if audit.risk_score is not None else None,
        correlation_id=audit.correlation_id,
        created_at=audit.created_at,
    )
