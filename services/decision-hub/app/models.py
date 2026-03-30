"""
SQLAlchemy ORM models for decision-hub.

WHY two tables:
  decision_rules  — rules as data, not code. Editable without redeployment.
  decision_audit  — immutable audit trail. Every decision is recorded with
                    full context snapshot so it can be replayed or explained.

The audit record answers: "What exactly was evaluated and why was the
decision made?" — a question no legacy if-else system can answer.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class DecisionRule(Base):
    __tablename__ = "decision_rules"

    rule_id: Mapped[str] = mapped_column(String, primary_key=True)
    version: Mapped[str] = mapped_column(String, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    condition_type: Mapped[str] = mapped_column(String, nullable=False)  # THRESHOLD | BLOCKLIST | COMPOSITE
    condition_params: Mapped[dict] = mapped_column(JSONB, nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)  # REJECT | CHALLENGE | APPROVE
    reason_code: Mapped[str] = mapped_column(String, nullable=False)
    owner: Mapped[str] = mapped_column(String, nullable=False)  # compliance | risk | fincontrol
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class DecisionAudit(Base):
    __tablename__ = "decision_audit"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    decision_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    transfer_context: Mapped[dict] = mapped_column(JSONB, nullable=False)   # full input snapshot
    rules_checked: Mapped[list] = mapped_column(JSONB, nullable=False)      # [{rule_id, matched, action}]
    rules_matched: Mapped[list] = mapped_column(JSONB, nullable=False)      # only matched rules
    final_decision: Mapped[str] = mapped_column(String, nullable=False)
    risk_score: Mapped[float | None] = mapped_column(Numeric(4, 2), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
