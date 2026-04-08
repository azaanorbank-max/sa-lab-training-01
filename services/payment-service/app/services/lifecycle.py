"""
Transfer lifecycle helpers.

Handles post-decision state transitions for approved transfers.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PaymentTransfer


async def apply_decided(
    transfer: PaymentTransfer,
    decision_id: str,
    db: AsyncSession,
) -> None:
    """Transition an approved transfer to DECIDED and persist the decision reference."""
    transfer.decision_id = uuid.UUID(decision_id)
    transfer.status = "DECIDED"
    transfer.updated_at = datetime.now(timezone.utc)
    await db.commit()
