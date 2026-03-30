# Decision Hub — Rules Catalog

## Seeded Rules

| rule_id       | version | priority | owner       | condition_type | action | reason_code              |
|---------------|---------|----------|-------------|----------------|--------|--------------------------|
| LIMIT_DAILY   | 1.0     | 1        | fincontrol  | THRESHOLD      | REJECT | DAILY_LIMIT_EXCEEDED     |
| AML_102       | 2.1     | 2        | compliance  | BLOCKLIST      | REJECT | AML_COUNTRY_BLOCKED      |
| FRAUD_017     | 1.3     | 3        | risk        | COMPOSITE      | REJECT | FRAUD_RISK_DEVICE_AMOUNT |

---

## Rule Definitions

### LIMIT_DAILY

```json
{
  "rule_id": "LIMIT_DAILY",
  "condition_type": "THRESHOLD",
  "condition_params": {
    "fields": ["daily_sum", "amount"],
    "operator": "SUM_GT",
    "threshold": 10000000
  },
  "action": "REJECT",
  "owner": "fincontrol"
}
```

**Logic**: If `daily_sum + amount > 10,000,000` → REJECT

**Why**: Daily transfer limit per client. Owned by Financial Control.
Changing this threshold previously required a code change + deployment.
Now it's a PATCH request.

**Demo**: Scenario B — change threshold and observe immediate effect.

---

### AML_102

```json
{
  "rule_id": "AML_102",
  "condition_type": "BLOCKLIST",
  "condition_params": {
    "field": "country",
    "blocked_values": ["IR", "KP", "CU", "SY"]
  },
  "action": "REJECT",
  "owner": "compliance"
}
```

**Logic**: If `country` is in the blocked list → REJECT

**Why**: AML regulation — sanctioned jurisdictions. Owned by Compliance.
The blocked list is in `condition_params.blocked_values` — editable via PATCH.
Previously this list was hardcoded in the payment service.

**Demo**: Scenario A — transfer to IR triggers this rule, audit shows owner.

---

### FRAUD_017

```json
{
  "rule_id": "FRAUD_017",
  "condition_type": "COMPOSITE",
  "condition_params": {
    "conditions": [
      {"field": "device_trust", "eq": "LOW"},
      {"field": "amount", "gt": 200000}
    ]
  },
  "action": "REJECT",
  "owner": "risk"
}
```

**Logic**: If `device_trust == "LOW"` AND `amount > 200,000` → REJECT

**Why**: High-value transfers from untrusted devices are high-risk.
Owned by Risk team. The thresholds are in `condition_params` — tunable.

---

## Condition Types

| type        | semantics                                      | example params                                              |
|-------------|------------------------------------------------|-------------------------------------------------------------|
| THRESHOLD   | Numeric comparison (field or sum of fields)    | `{fields: ["a","b"], operator: "SUM_GT", threshold: N}`    |
| BLOCKLIST   | Field value must not be in a set              | `{field: "country", blocked_values: ["IR","KP"]}`           |
| COMPOSITE   | All sub-conditions must match (AND logic)      | `{conditions: [{field: "x", eq: "Y"}, {field: "z", gt: N}]}` |

---

## Evaluation Strategy

1. Rules are loaded ordered by `priority` (lower = evaluated first)
2. First `REJECT` rule that matches → **stop, return REJECT**
   - Rationale: no point fraud-scoring if country is sanctioned
3. `CHALLENGE` rules accumulate — do not stop evaluation
4. If no REJECT and no CHALLENGE → **APPROVE**

---

## Changing Rules at Runtime

```bash
# Lower the daily limit without redeployment
curl -X PATCH http://localhost:8002/decision/rules/LIMIT_DAILY \
  -H "Content-Type: application/json" \
  -d '{"condition_params": {"fields": ["daily_sum","amount"], "operator": "SUM_GT", "threshold": 100000}}'

# Disable a rule entirely
curl -X PATCH http://localhost:8002/decision/rules/FRAUD_017 \
  -H "Content-Type: application/json" \
  -d '{"active": false}'

# View current state of all rules
curl http://localhost:8002/decision/rules
```

Changes are:
- **Immediate** — next evaluation uses new params
- **Traceable** — `updated_at` timestamp updated
- **Auditable** — all past decisions still reference the params that were active when they ran (snapshot in `decision_audit.rules_checked`)

---

## Adding New Rules

In this sandbox, insert directly into `decision_rules`:

```sql
INSERT INTO decision_rules VALUES (
  'AML_HIGH_RISK_AMOUNT', '1.0', 4, true,
  'THRESHOLD',
  '{"fields": ["amount"], "operator": "SUM_GT", "threshold": 5000000}',
  'CHALLENGE', 'HIGH_AMOUNT_REVIEW', 'risk', NOW()
);
```

In production, this would go through a rule management UI backed by this API.
