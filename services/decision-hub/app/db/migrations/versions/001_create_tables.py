"""create decision_hub tables

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
        "decision_rules",
        sa.Column("rule_id", sa.String(), nullable=False),
        sa.Column("version", sa.String(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("condition_type", sa.String(), nullable=False),
        sa.Column("condition_params", JSONB(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("reason_code", sa.String(), nullable=False),
        sa.Column("owner", sa.String(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("rule_id"),
    )

    op.create_table(
        "decision_audit",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("decision_id", UUID(as_uuid=True), nullable=False),
        sa.Column("transfer_context", JSONB(), nullable=False),
        sa.Column("rules_checked", JSONB(), nullable=False),
        sa.Column("rules_matched", JSONB(), nullable=False),
        sa.Column("final_decision", sa.String(), nullable=False),
        sa.Column("risk_score", sa.Numeric(4, 2), nullable=True),
        sa.Column("correlation_id", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_decision_audit_decision_id", "decision_audit", ["decision_id"])


def downgrade() -> None:
    op.drop_index("ix_decision_audit_decision_id", table_name="decision_audit")
    op.drop_table("decision_audit")
    op.drop_table("decision_rules")
