"""
SQLAlchemy ORM models for payment-service.

payment_transfers — the transfer entity. Owns the status lifecycle.
payment_idempotency — the idempotency store. Caches responses for replay.

WHY a separate idempotency table (not just a unique key on transfers):
  The idempotency table stores the full response snapshot. When the same
  Idempotency-Key arrives again, we return the exact same HTTP response
  that was returned the first time — status code, body, everything.

  This means the client cannot distinguish a retry from a fresh call.
  That is the entire point: idempotency makes retries safe.

STATUS MACHINE:
  NEW → DECIDED → POSTED      (happy path)
  NEW → DECIDED → FAILED      (ledger failure)
  NEW → REJECTED              (decision hub said REJECT)
  NEW → FAILED                (decision hub unreachable)

  Each transition is logged with correlation_id.
  No implicit transitions. No shortcuts.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class PaymentTransfer(Base):
    __tablename__ = "payment_transfers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    idempotency_key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    client_id: Mapped[str] = mapped_column(String, nullable=False)
    receiver_id: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    country: Mapped[str] = mapped_column(String(2), nullable=False)
    device_trust: Mapped[str] = mapped_column(String, nullable=False)   # HIGH | MEDIUM | LOW
    daily_sum: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="NEW")
    decision_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class PaymentIdempotency(Base):
    __tablename__ = "payment_idempotency"

    idempotency_key: Mapped[str] = mapped_column(String, primary_key=True)
    transfer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    response_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
