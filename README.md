<<<<<<< HEAD
# Decision Hub — Bank Runtime Sandbox

A production-like reference architecture showing how to replace scattered banking decision logic with a centralized, explainable, auditable Decision Hub.

**For system analysts learning to think as engineers.**

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Client (curl / mobile app)                                     │
│         │                                                       │
│         ▼                                                       │
│  api-gateway        :8000  ── security boundary,                │
│                              X-Correlation-Id injection,        │
│                              routing, NO business logic         │
│         │                                                       │
│         ▼                                                       │
│  payment-service    :8001  ── owns transfer lifecycle,          │
│                              idempotency, status machine        │
│         │                          │                           │
│         ▼                          ▼                           │
│  decision-hub       :8002  ledger-mock :8003                   │
│  rules as data,            simulates posting,                  │
│  audit trail,              can fail on demand                  │
│  explainability                                                 │
│                                                                 │
│  ──────────────── PostgreSQL 16 ────────────────────────────── │
│  payment_transfers  payment_idempotency                         │
│  decision_rules     decision_audit                              │
│  ledger_postings                                                │
└─────────────────────────────────────────────────────────────────┘
```

**Ownership is explicit:**

| Service          | Owns                                          | Does NOT own                  |
|------------------|-----------------------------------------------|-------------------------------|
| api-gateway      | Context propagation, routing, rate-limit headers | Any business logic          |
| payment-service  | Transfer entity, status transitions, idempotency | Decision logic             |
| decision-hub     | Rules evaluation, audit trail, explainability | Transfer state              |
| ledger-mock      | Money movement simulation                     | Decisions, transfer status    |

---

## Quick Start

```bash
cp .env.example .env
docker compose up --build
```

Services start in dependency order:
`postgres → decision-hub + ledger-mock → payment-service → api-gateway`

Verify everything is running:
```bash
curl http://localhost:8000/health   # api-gateway
curl http://localhost:8001/health   # payment-service
curl http://localhost:8002/health   # decision-hub
curl http://localhost:8003/health   # ledger-mock
```

Run all demo scenarios:
```bash
./scripts/demo.sh
```

Or individually: `./scripts/demo.sh A`

---

## 4 Demo Scenarios

### Scenario A — Explainability

**Question: Why was this transaction rejected?**

```bash
# TO-BE: structured, traceable
curl -s -X POST http://localhost:8000/api/p2p/transfer \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: test-a-001" \
  -d '{
    "client_id": "client-001", "receiver_id": "rec-001",
    "amount": 50000, "currency": "KZT",
    "country": "IR", "device_trust": "HIGH", "daily_sum": 0
  }'
```

Response includes:
```json
{
  "status": "REJECTED",
  "decision": {
    "decision_id": "...",
    "reasons": [{"rule_id": "AML_102", "reason_code": "AML_COUNTRY_BLOCKED", "owner": "compliance"}],
    "risk_score": 0.95,
    "rules_evaluated": 3
  }
}
```

Fetch the full audit record:
```bash
curl http://localhost:8002/decision/audit/{decision_id}
```

```bash
# AS-IS: unstructured, unauditable
curl -s -X POST http://localhost:8000/api/p2p/transfer-legacy \
  -H "Idempotency-Key: test-a-002" \
  -H "Content-Type: application/json" \
  -d '{"client_id": "c1", "receiver_id": "r1", "amount": 50000, "currency": "KZT", "country": "IR", "device_trust": "HIGH", "daily_sum": 0}'
```

Response: `{"status": "REJECTED", "reason": "AML_BLOCKED"}` — that's all you get.

---

### Scenario B — Change Rule Without Release

**Goal: lower the daily limit immediately without redeployment.**

```bash
# Step 1: this transfer passes (500K < 10M limit)
curl -s -X POST http://localhost:8000/api/p2p/transfer \
  -H "Idempotency-Key: test-b-001" \
  -H "Content-Type: application/json" \
  -d '{"client_id":"c1","receiver_id":"r1","amount":500000,"currency":"KZT","country":"KZ","device_trust":"HIGH","daily_sum":0}'

# Step 2: lower the threshold to 100,000 (no code change, no deploy)
curl -X PATCH http://localhost:8002/decision/rules/LIMIT_DAILY \
  -H "Content-Type: application/json" \
  -d '{"condition_params": {"fields": ["daily_sum","amount"], "operator": "SUM_GT", "threshold": 100000}}'

# Step 3: same transfer now fails (500K > 100K)
curl -s -X POST http://localhost:8000/api/p2p/transfer \
  -H "Idempotency-Key: test-b-002" \
  -H "Content-Type: application/json" \
  -d '{"client_id":"c1","receiver_id":"r1","amount":500000,"currency":"KZT","country":"KZ","device_trust":"HIGH","daily_sum":0}'

# Step 4: restore
curl -X PATCH http://localhost:8002/decision/rules/LIMIT_DAILY \
  -H "Content-Type: application/json" \
  -d '{"condition_params": {"fields": ["daily_sum","amount"], "operator": "SUM_GT", "threshold": 10000000}}'
```

payment-service code did not change. Zero deployments.

---

### Scenario C — Idempotency

**Goal: retries are safe. No duplicate money movement.**

```bash
# First call
curl -s -X POST http://localhost:8000/api/p2p/transfer \
  -H "Idempotency-Key: stable-key-001" \
  -H "Content-Type: application/json" \
  -d '{"client_id":"c1","receiver_id":"r1","amount":10000,"currency":"KZT","country":"KZ","device_trust":"HIGH","daily_sum":0}'

# Retry with same key (network failure simulation)
curl -s -X POST http://localhost:8000/api/p2p/transfer \
  -H "Idempotency-Key: stable-key-001" \
  -H "Content-Type: application/json" \
  -d '{"client_id":"c1","receiver_id":"r1","amount":10000,"currency":"KZT","country":"KZ","device_trust":"HIGH","daily_sum":0}'
```

Both responses have the same `transfer_id`. One ledger posting exists.
The second response includes `"idempotent": true`.

---

### Scenario D — Partial Failure

**Goal: DECIDED ≠ POSTED. Status machine is explicit.**

```bash
# Step 1: force ledger to fail
curl -s -X POST http://localhost:8000/api/p2p/transfer \
  -H "Idempotency-Key: test-d-001" \
  -H "X-Fail-Mode: ERROR" \
  -H "Content-Type: application/json" \
  -d '{"client_id":"c1","receiver_id":"r1","amount":25000,"currency":"KZT","country":"KZ","device_trust":"HIGH","daily_sum":0}'
```

Response: `{"status": "FAILED", "decision": {"decision": "APPROVE", ...}}`

Decision hub approved it. Ledger failed it. These are separate facts.
`status=FAILED` means money did NOT move.

```bash
# Step 2: retry without fail mode (succeeds)
curl -s -X POST http://localhost:8000/api/p2p/transfer \
  -H "Idempotency-Key: test-d-002" \
  -H "Content-Type: application/json" \
  -d '{"client_id":"c1","receiver_id":"r1","amount":25000,"currency":"KZT","country":"KZ","device_trust":"HIGH","daily_sum":0}'
```

Response: `{"status": "POSTED", ...}`

---

## AS-IS vs TO-BE

| Capability                         | AS-IS (legacy)                    | TO-BE (Decision Hub)                     |
|------------------------------------|-----------------------------------|------------------------------------------|
| Where does decision logic live?    | Inside each service (code)        | decision-hub (data + engine)             |
| Why was this rejected?             | Free-text string in response      | Structured: rule_id, reason_code, owner  |
| Who owns this rule?                | Nobody / git blame                | `owner` field per rule                   |
| Change a threshold                 | Code → PR → deploy (days)         | PATCH /decision/rules (seconds)          |
| Audit trail                        | None                              | decision_audit table, every decision     |
| Rule versioning                    | Git history                       | version + updated_at per rule            |
| Test a rule change                 | Deploy to staging                 | PATCH + single API call                  |
| Duplicate protection               | Depends on service                | Idempotency-Key enforced at gateway      |
| Failure traceability               | Logs (if they exist)              | Status machine + correlation_id          |
| Add logic to new service           | Copy-paste (diverges over time)   | Call decision-hub (one source of truth)  |

---

## Transfer Status Lifecycle

```
NEW → DECIDED → POSTED      (happy path)
NEW → DECIDED → FAILED      (ledger failure)
NEW → REJECTED              (decision hub said REJECT)
NEW → FAILED                (decision hub unreachable)
```

| Status     | Meaning                               | Money moved? |
|------------|---------------------------------------|--------------|
| NEW        | Transfer record created               | No           |
| DECIDED    | Hub approved, ledger call pending     | No           |
| POSTED     | Ledger confirmed posting              | YES          |
| REJECTED   | Rule rejected the transfer            | No           |
| FAILED     | Infrastructure failure                | No           |

Every transition logs: `{event: "status_transition", from_status, to_status, transfer_id, correlation_id}`

---

## Decision Rules

| rule_id       | version | priority | owner       | condition                               | action |
|---------------|---------|----------|-------------|-----------------------------------------|--------|
| LIMIT_DAILY   | 1.0     | 1        | fincontrol  | daily_sum + amount > 10,000,000         | REJECT |
| AML_102       | 2.1     | 2        | compliance  | country in [IR, KP, CU, SY]            | REJECT |
| FRAUD_017     | 1.3     | 3        | risk        | device_trust=LOW AND amount > 200,000   | REJECT |

Rules evaluate in priority order. First REJECT stops evaluation.

```bash
# View all rules
curl http://localhost:8002/decision/rules

# Change LIMIT_DAILY threshold
curl -X PATCH http://localhost:8002/decision/rules/LIMIT_DAILY \
  -H "Content-Type: application/json" \
  -d '{"condition_params": {"fields": ["daily_sum","amount"], "operator": "SUM_GT", "threshold": 5000000}}'
```

---

## Observability

### Correlation ID

Every request gets an `X-Correlation-Id`. Generated by api-gateway if client doesn't provide one.
Propagated through all service calls. Included in every log line and error response.

```bash
# Trace a specific request across all service logs
docker compose logs | grep "corr-xyz-123"
```

### Structured Logs

Every log line is JSON:
```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "service": "payment-service",
  "level": "INFO",
  "correlation_id": "abc-123",
  "event": "status_transition",
  "transfer_id": "uuid-...",
  "from_status": "DECIDED",
  "to_status": "POSTED"
}
```

### Audit Table

```sql
-- Every decision, forever
SELECT * FROM decision_audit WHERE correlation_id = 'abc-123';

-- What rules fired in the last hour?
SELECT rules_matched, final_decision, created_at
FROM decision_audit
WHERE created_at > NOW() - INTERVAL '1 hour';

-- FAILED transfers needing investigation
SELECT id, status, correlation_id, created_at
FROM payment_transfers
WHERE status = 'FAILED'
ORDER BY created_at DESC;
```

---

## Educational Notes for SA Engineers

### What each service teaches

**api-gateway** — The difference between routing and logic. A gateway's job is to propagate context and route requests. The moment it makes a business decision, it has become a service that nobody asked for.

**payment-service** — What "owning an entity" means. Payment-service owns transfers. It knows their status. It does not decide whether a transfer is allowed (that's decision-hub) and it does not move money (that's ledger). Separation of concerns is not a style preference — it's what makes the system debuggable.

**decision-hub** — Why rules-as-data beats rules-as-code. Code changes require deployments, reviews, and risk. Data changes require a PATCH. The moment you put a business threshold in a `if amount > 10_000_000` statement, you've given that number to the engineering team instead of the business owner.

**ledger-mock** — Why idempotency is not optional. The ledger is called over a network. Networks fail. Clients retry. Without idempotency at the ledger level, every retry is a potential double-debit. The `unique constraint on transfer_id` is a design decision, not a database detail.

**transfer_legacy.py** — Read this and ask: "Who do I call if AML_102 needs updating?" The code answers: a developer. Decision Hub answers: the compliance team, via API, without a developer.

### The real lesson

A system analyst who documents "the system rejects transfers to sanctioned countries" has described a requirement.

An engineer-level analyst asks:
- Which service checks this?
- What is the exact list of countries?
- Who owns it?
- How does it get updated?
- What happens when the check fails?
- How do I know it worked?
- How do I audit it six months later?

This codebase answers all of those questions structurally — not in a Word document.

---

## Project Structure

```
/
├── docker-compose.yml
├── .env.example
├── contracts/           # OpenAPI specs (source of truth for all APIs)
├── docs/                # PlantUML diagrams + lifecycle docs
├── scripts/demo.sh      # 4 demo scenarios with curl
├── shared/              # logging.py + correlation.py (used by all services)
└── services/
    ├── api-gateway/     # routing, context propagation
    ├── payment-service/ # transfer lifecycle, idempotency
    ├── decision-hub/    # rule engine, audit trail
    └── ledger-mock/     # posting simulation
```

---

## Tech Stack

- Python 3.12, FastAPI, Uvicorn
- PostgreSQL 16
- SQLAlchemy 2.x async + Alembic migrations
- Pydantic v2
- httpx for service-to-service calls
- Structured JSON logging + X-Correlation-Id across all services
- Docker + docker-compose
=======
# sa-lab
Reverse Engineering
>>>>>>> d0affe1dc8dd5ea6587c9c8c6f57e4a01b8346e0
