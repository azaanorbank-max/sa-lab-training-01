"""seed decision_rules with initial rule set

Revision ID: 002
Revises: 001
Create Date: 2024-01-01 00:01:00.000000

WHY a data migration for seed data:
  Rules are versioned, owned, and auditable — just like schema.
  Putting them in a migration means the system starts in a known,
  reproducible state. A new developer or a fresh environment gets
  exactly the same rule set as production.

  Business owners are listed in 'owner' field — this is intentional.
  Every rule has a clear stakeholder who is accountable for it.
"""
import json
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RULES = [
    {
        "rule_id": "LIMIT_DAILY",
        "version": "1.0",
        "priority": 1,
        "active": True,
        "condition_type": "THRESHOLD",
        "condition_params": json.dumps({
            "fields": ["daily_sum", "amount"],
            "operator": "SUM_GT",
            "threshold": 10000000,
        }),
        "action": "REJECT",
        "reason_code": "DAILY_LIMIT_EXCEEDED",
        "owner": "fincontrol",
        "updated_at": datetime.now(timezone.utc),
    },
    {
        "rule_id": "AML_102",
        "version": "2.1",
        "priority": 2,
        "active": True,
        "condition_type": "BLOCKLIST",
        "condition_params": json.dumps({
            "field": "country",
            "blocked_values": ["IR", "KP", "CU", "SY"],
        }),
        "action": "REJECT",
        "reason_code": "AML_COUNTRY_BLOCKED",
        "owner": "compliance",
        "updated_at": datetime.now(timezone.utc),
    },
    {
        "rule_id": "FRAUD_017",
        "version": "1.3",
        "priority": 3,
        "active": True,
        "condition_type": "COMPOSITE",
        "condition_params": json.dumps({
            "conditions": [
                {"field": "device_trust", "eq": "LOW"},
                {"field": "amount", "gt": 200000},
            ]
        }),
        "action": "REJECT",
        "reason_code": "FRAUD_RISK_DEVICE_AMOUNT",
        "owner": "risk",
        "updated_at": datetime.now(timezone.utc),
    },
]


def upgrade() -> None:
    rules_table = sa.table(
        "decision_rules",
        sa.column("rule_id", sa.String),
        sa.column("version", sa.String),
        sa.column("priority", sa.Integer),
        sa.column("active", sa.Boolean),
        sa.column("condition_type", sa.String),
        sa.column("condition_params", sa.Text),
        sa.column("action", sa.String),
        sa.column("reason_code", sa.String),
        sa.column("owner", sa.String),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    # Insert only if not already present (idempotent seed)
    conn = op.get_bind()
    for rule in RULES:
        exists = conn.execute(
            sa.text("SELECT 1 FROM decision_rules WHERE rule_id = :rule_id"),
            {"rule_id": rule["rule_id"]},
        ).fetchone()
        if not exists:
            op.bulk_insert(rules_table, [rule])


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM decision_rules WHERE rule_id IN ('LIMIT_DAILY', 'AML_102', 'FRAUD_017')")
    )
