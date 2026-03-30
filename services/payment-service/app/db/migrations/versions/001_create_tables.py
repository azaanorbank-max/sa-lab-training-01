"""create payment_service tables

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "payment_transfers",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("idempotency_key", sa.String(), nullable=False),
        sa.Column("client_id", sa.String(), nullable=False),
        sa.Column("receiver_id", sa.String(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("country", sa.String(2), nullable=False),
        sa.Column("device_trust", sa.String(), nullable=False),
        sa.Column("daily_sum", sa.Numeric(18, 2), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="NEW"),
        sa.Column("decision_id", UUID(as_uuid=True), nullable=True),
        sa.Column("correlation_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )

    op.create_table(
        "payment_idempotency",
        sa.Column("idempotency_key", sa.String(), nullable=False),
        sa.Column("transfer_id", UUID(as_uuid=True), nullable=False),
        sa.Column("response_snapshot", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("idempotency_key"),
    )


def downgrade() -> None:
    op.drop_table("payment_idempotency")
    op.drop_table("payment_transfers")
