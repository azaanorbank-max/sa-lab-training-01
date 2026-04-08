# Decision Hub — System Analysis Assignment

---

## About This Assignment

This repository contains a working implementation of a P2P payment processing system built around a centralized Decision Hub. The codebase is real: it runs, it connects to a database, it makes HTTP calls between services, it logs structured events, and it fails in realistic ways.

**Your role:** You are a system analyst who has just been assigned to this project. The existing documentation is incomplete and partially outdated. Your job is to read the code, infer the actual system behavior, identify engineering problems, and produce structured analytical outputs.

**This is not a theoretical exercise.** Every question in this assignment refers to specific files, functions, or behaviors you can observe directly in the code. Do not answer from general knowledge — answer from what you read.

**What to expect:**
- Some things in the code are correctly implemented
- Some things have engineering problems that affect correctness, auditability, or observability
- Some problems only appear under specific conditions (retries, concurrent requests, failures)
- Your job is to find the problems and explain them with precision — not just flag that something "looks wrong"

---

## Business Context

A retail bank operates a P2P transfer product that allows customers to send money to other customers. The bank operates under the following requirements:

- **Compliance:** Transfers to sanctioned countries must be blocked. The rules enforcing this must be owned by named business stakeholders, versioned, and auditable.
- **Auditability:** Every transfer decision must be fully traceable. Regulators may request a complete audit record — which rule fired, who owns it, what the input context was — for any transaction at any time.
- **Reliability:** Client retries must not cause duplicate money movement. A network timeout on the client side must never result in a double debit.
- **Observability:** Every request must be traceable across all internal services using a shared correlation identifier. Engineers must be able to reconstruct any transaction's full lifecycle from logs alone.
- **Changeability:** Business rules (limits, blocklists, thresholds) must be changeable by business stakeholders without code deployments or engineering involvement.

The system was partially migrated from a legacy architecture ("AS-IS") to a new Decision Hub architecture ("TO-BE"). Both implementations exist in the codebase simultaneously. Part of your analysis involves understanding the differences between them and identifying where the migration introduced problems.

---

## System Architecture

```
Client (mobile app / curl)
         │
         ▼
api-gateway                    :8000
[routing, X-Correlation-Id injection, header forwarding]
         │
         ▼
payment-service                :8001
[transfer lifecycle, idempotency, orchestration]
         │                           │
         ▼                           ▼
decision-hub                   ledger-mock
:8002                          :8003
[rules evaluation,             [posting simulation,
 audit trail,                   idempotency by transfer_id,
 explainability]                configurable failure modes]

────────────────── PostgreSQL 16 ─────────────────────────────
payment_transfers      payment_idempotency
decision_rules         decision_audit
ledger_postings
```

---

## Services in Scope

**api-gateway** (port 8000)
Routes requests from external clients to payment-service. Generates or forwards `X-Correlation-Id`. Forwards `Idempotency-Key` and `X-Fail-Mode` headers downstream. Does not evaluate business rules, does not store state.

**payment-service** (port 8001)
Owns the transfer entity and its lifecycle. Manages transfer creation, status transitions, and idempotency enforcement. Orchestrates calls to decision-hub and ledger-mock. Implements both the TO-BE flow (`POST /p2p/transfer`) and the legacy AS-IS flow (`POST /p2p/transfer-legacy`).

**decision-hub** (port 8002)
Evaluates business rules against the transfer context. Rules are stored as data in the database — they are not code. Every evaluation is recorded in an immutable audit table with full input context, all rules checked, and the final decision. Exposes admin endpoints to view and update rules without redeployment.

**ledger-mock** (port 8003)
Simulates the core banking ledger (posting engine). Accepts posting instructions and records them. Implements its own idempotency: the same `transfer_id` is never posted twice. Supports configurable failure modes (`TIMEOUT`, `ERROR`) for testing partial-failure scenarios.

---

## How to Work Through This Assignment

**Recommended reading order:**
1. [services/payment-service/app/main.py](services/payment-service/app/main.py) — read the module docstring to understand ownership boundaries
2. [services/payment-service/app/routes/transfer.py](services/payment-service/app/routes/transfer.py) — the main transfer flow in full
3. [services/decision-hub/app/engine/rule_engine.py](services/decision-hub/app/engine/rule_engine.py) — how decisions are evaluated
4. [contracts/payment-service.openapi.yaml](contracts/payment-service.openapi.yaml) and [contracts/decision-hub.openapi.yaml](contracts/decision-hub.openapi.yaml) — the documented API contracts
5. Then proceed with the flow-based tasks below

**Where to look:**
- Business rules: [services/decision-hub/app/db/migrations/versions/002_seed_rules.py](services/decision-hub/app/db/migrations/versions/002_seed_rules.py)
- Transfer status machine: [services/payment-service/app/routes/transfer.py](services/payment-service/app/routes/transfer.py) + [services/payment-service/app/models.py](services/payment-service/app/models.py)
- Correlation ID propagation: [shared/correlation.py](shared/correlation.py) + all `*_client.py` files
- API contracts: [contracts/](contracts/) directory

**Important:** The `docs/` directory contains documentation that may not match the current code. When there is a discrepancy between documentation and code, treat the **code as the source of truth** — it is what the system actually does.

---

---

# FLOW 1: IDEMPOTENCY / RETRY SAFETY

**Analytical objective:** Verify whether the system correctly prevents duplicate side effects when clients retry requests. Identify whether the idempotency guard is placed at the correct point in the execution flow relative to any state-changing database operations.

**Files relevant to this flow:**

| File | Role in this flow |
|---|---|
| [services/payment-service/app/routes/transfer.py](services/payment-service/app/routes/transfer.py) | Main handler — idempotency check and transfer creation |
| [services/payment-service/app/models.py](services/payment-service/app/models.py) | `PaymentTransfer` and `PaymentIdempotency` table definitions |
| [services/payment-service/app/services/ledger_client.py](services/payment-service/app/services/ledger_client.py) | How payment-service calls ledger-mock |
| [services/ledger-mock/app/main.py](services/ledger-mock/app/main.py) | How ledger-mock handles duplicate posting requests |
| [contracts/payment-service.openapi.yaml](contracts/payment-service.openapi.yaml) | `Idempotency-Key` header documentation |

---

## Task 1.0 — Warm-up
### How Does the Idempotency Mechanism Work?
`[~15 min | reading only | no code changes required]`

---

**Your situation:**

You are a system analyst who has just joined the team. Your tech lead says:

> *"Before we get into the architecture review, read how we handle idempotency. It is one of the most important properties of the system — and the one developers most commonly get wrong on first implementation. Tell me how ours works."*

You have not attended any onboarding yet. Your only source is the code.

---

**System context:**

When a client sends a transfer request, they include an `Idempotency-Key` header. This key represents a single logical transfer attempt. If the client's network connection fails after sending the request but before receiving the response, the client will retry the same request with the same key. The server must detect that this is a retry and return the exact same response — without processing the transfer a second time.

This is not optional in payment systems. Without idempotency, every network failure is a potential double debit.

---

**What to read:**

Open [services/payment-service/app/routes/transfer.py](services/payment-service/app/routes/transfer.py) and read `create_transfer()` from top to bottom. The docstring at the top describes the intended flow in numbered steps. Then open [services/payment-service/app/models.py](services/payment-service/app/models.py) and read the `PaymentIdempotency` model.

---

**Your tasks:**

Answer each of the following based only on what you observe in the code — not from memory or general knowledge:

1. What HTTP status code and `error_code` value does the service return if the `Idempotency-Key` header is absent from the request?
2. What is the name of the database table that stores idempotency records? What column serves as its primary key?
3. What is stored in the `response_snapshot` column? Give a concrete example of what this column would contain for a successfully posted transfer.
4. Which field in the API response indicates to the client that the response is a replay rather than a fresh execution?
5. In the happy-path flow (transfer approved and posted), at what point in the execution sequence is the idempotency record written to the database — before or after the ledger-mock call? Does the order matter?

**Expected output:** Short written answers to each question. No code changes required.

---

## Task 1.1 — Main Task
### Idempotency Implementation Audit: Is the Retry Path Actually Safe?
`[~35 min | code reading + analysis + written output]`

---

**Your situation:**

A production incident has been filed. The on-call engineer noticed entries in the `payment_transfers` table with `status = 'NEW'` and no `decision_id`, no corresponding `decision_audit` record, and no ledger posting. These records appeared during a period of elevated client-side retry activity following a network instability event.

The incident was closed with the note: *"No customer-facing impact observed. Root cause under investigation."* You have been assigned to determine the root cause.

The engineering team tells you: *"The idempotency check is there — look at step 2 in the code. It fires correctly."*

You are not sure that is the full story.

---

**System context:**

Idempotency protection requires a specific ordering of operations:

1. **Check** whether this request has been processed before (query the idempotency store)
2. **If a record is found** — return the cached response immediately, without executing any business logic
3. **If no record is found** — execute the business logic (create records, call services, change state)
4. **After execution completes** — save the complete response to the idempotency store for future replays

The key invariant: **the check must happen before any side effect.** A side effect (such as a database write) that occurs before the idempotency check is not protected by the mechanism. On retry, that side effect will be executed again before the check has a chance to intercept.

---

**What to read:**

Open [services/payment-service/app/routes/transfer.py](services/payment-service/app/routes/transfer.py). Read `create_transfer()` carefully. The docstring at the top lists the intended steps in order. Your job is to verify whether the actual code follows the same order.

Then open [services/payment-service/app/models.py](services/payment-service/app/models.py) and find the `PaymentTransfer` model. Look specifically at the `idempotency_key` field definition.

---

**Your tasks:**

**Step 1 — Map the intended steps to the actual code.**

The docstring in `create_transfer()` lists the intended steps. For each step, identify where it appears in the actual code and whether it occurs before or after the first database write (`db.add()` + `await db.commit()`):

| Step (from docstring) | What it does | Position relative to first DB write |
|---|---|---|
| Step 1 | Validate `Idempotency-Key` header | |
| Step 2 | Check idempotency store | |
| Step 3 | Create transfer record | |
| Step 4 | Call decision-hub | |

**Step 2 — Identify the ordering problem.**

Based on your mapping: does the idempotency check (Step 2) happen *before* or *after* the `PaymentTransfer` record is created and committed to the database (Step 3)?

If the order is inverted, answer:
- What is the side effect that occurs before the deduplication guard fires?
- What specific operation in the code constitutes this side effect?

**Step 3 — Model the retry behavior.**

Assume a client sends the same request twice with the same `Idempotency-Key`. Trace both requests through the code:

| Event | First request | Second request (retry) |
|---|---|---|
| Is a `PaymentTransfer` row created? | | |
| Does the idempotency check fire? | | |
| What does the check find? | | |
| What HTTP response is returned? | | |
| Final state of `payment_transfers` table | | |
| Final state of `payment_idempotency` table | | |

**Step 4 — Analyze the database constraint.**

Look at the `PaymentTransfer` model in `models.py`. Is there a database-level constraint that prevents two rows from sharing the same `idempotency_key`?

- If the constraint exists: what happens during the retry before the idempotency check fires?
- If the constraint is absent: what is the state of the `payment_transfers` table after the retry completes, from the perspective of the API response versus the database?

**Step 5 — Propose the correct implementation.**

Describe in 3–5 sentences what the correct order of operations should be. You do not need to write code — describe the correct behavior in plain language.

Then answer: what database constraint should exist on `PaymentTransfer.idempotency_key`, and why is it a necessary companion to the application-level check?

---

**Expected output:**
- Completed mapping table from Step 1
- 2–3 sentences for Step 2
- Completed trace table from Step 3
- 3–4 sentences for Step 4
- 3–5 sentences for Step 5

---

## Task 1.2 — Main Task
### Retry Scenario: Full Execution Trace
`[~25 min | scenario analysis + written execution trace]`

---

**Your situation:**

A client submits a P2P transfer for 25,000 KZT to country KZ with `device_trust=HIGH`. Everything proceeds normally through the decision-hub call (approved). The payment-service then calls ledger-mock — and the connection times out. The client never receives a response. Five seconds later, the client retries the exact same request with the same `Idempotency-Key`.

Your job is to trace exactly what happens — at both the API and database level — across both requests.

---

**System context:**

A transfer in this system goes through multiple phases:
- Decision-hub is called first and produces an `APPROVE`, `REJECT`, or `CHALLENGE` outcome
- If approved, ledger-mock is called to record the money movement
- Each phase has a corresponding status in `payment_transfers`

A timeout on the ledger call means payment-service received no success or failure response from the ledger. The transfer was approved but the posting outcome is unknown from payment-service's perspective.

---

**What to read:**

| File | What to look for |
|---|---|
| [services/payment-service/app/routes/transfer.py](services/payment-service/app/routes/transfer.py) | How ledger timeouts are handled (around step 7), what status is set |
| [services/payment-service/app/services/ledger_client.py](services/payment-service/app/services/ledger_client.py) | Timeout value, what exception class is raised on timeout |
| [services/ledger-mock/app/main.py](services/ledger-mock/app/main.py) | How ledger-mock handles a duplicate `transfer_id` |
| [services/payment-service/app/models.py](services/payment-service/app/models.py) | Which status is persisted after a ledger call failure |

---

**Your tasks:**

**Step 1 — Trace the first request.**

List every significant operation in order. Include: header validation, idempotency check, DB writes, external calls, exception handling, status updates, and the final response:

```
1. Client sends POST /p2p/transfer  (Idempotency-Key: K1)
2. [your trace — each step on a new line]
...
N. Client receives: [what HTTP status? what body fields?]

Final database state:
  payment_transfers:     status = ?
  payment_idempotency:   record exists? response_snapshot contains?
  ledger_postings:       record exists?
```

**Step 2 — Trace the retry.**

The client resends the same request 5 seconds later. Trace again:

```
1. Client sends POST /p2p/transfer  (Idempotency-Key: K1)  [RETRY]
2. [your trace]
...
N. Client receives: [what HTTP status? what body fields?]

Final database state:
  payment_transfers:     how many rows? status?
  payment_idempotency:   what does the record contain?
  ledger_postings:       record exists?
```

**Step 3 — Answer the key questions:**

1. Did money move on the first request? On the retry?
2. Is it possible that the ledger-mock actually completed the posting even though payment-service received a timeout exception? If yes: what does ledger-mock do when payment-service sends the posting request a second time with the same `transfer_id`?
3. What is the final `status` visible to the client via `GET /p2p/transfers/{id}` after the retry? Is this the correct status given what actually happened at the ledger?

---

## Task 1.3 — Senior Task
### Two-Level Idempotency: Payment-Service vs Ledger-Mock
`[~35 min | architectural analysis + written comparison]`

---

**Your situation:**

A senior engineer on the team says: *"We have two separate idempotency mechanisms in this system, and they protect against different failure modes. Most analysts only look at one of them."*

Your job is to identify both mechanisms, understand precisely what each one protects against, and determine whether there are scenarios that neither one covers.

---

**System context:**

In distributed systems, idempotency must be enforced at each level of the call chain independently. A retry from the client reaches payment-service; a retry from payment-service reaches ledger-mock. If either leg lacks idempotency, that leg is exposed to duplicate execution.

---

**What to read:**

| File | What to look for |
|---|---|
| [services/payment-service/app/routes/transfer.py](services/payment-service/app/routes/transfer.py) | The `PaymentIdempotency` lookup — what key is used |
| [services/payment-service/app/models.py](services/payment-service/app/models.py) | `PaymentIdempotency` table — what it stores |
| [services/ledger-mock/app/main.py](services/ledger-mock/app/main.py) | Duplicate posting check — what key is used |
| [services/payment-service/app/services/ledger_client.py](services/payment-service/app/services/ledger_client.py) | What is passed to the ledger in the request |

---

**Your tasks:**

**Part A — Compare the two mechanisms:**

| Dimension | Payment-service idempotency | Ledger-mock idempotency |
|---|---|---|
| Deduplication key | | |
| Where is the key generated? | | |
| What database table stores it? | | |
| What is returned on a duplicate request? | | |
| What failure scenario does it protect against? | | |

**Part B — Find the coverage gap:**

1. Is the client-provided `Idempotency-Key` header forwarded from payment-service to ledger-mock? If not, should it be? What is the architectural difference between using `Idempotency-Key` and using `transfer_id` as the ledger-level deduplication key?
2. Describe a specific sequence of events where payment-service's idempotency check operates correctly but ledger-mock still receives two posting requests for the same transfer. Is this theoretically possible?
3. Describe a specific sequence where ledger-mock's deduplication fires and prevents a double posting — but payment-service has two competing `PaymentTransfer` records in the database for the same logical transfer. What is the state discrepancy?

**Part C — Architectural assessment:**

In 3–5 sentences: is the current two-level idempotency design sufficient for production use? What specific change — to code ordering, database constraints, or both — would make the retry path fully safe?

---

---

# FLOW 2: TRANSFER STATUS MACHINE

**Analytical objective:** Reconstruct the complete transfer status machine from the code. Identify whether status transition logic is centralized in a single authoritative location, or scattered across multiple files with no single source of truth.

**Files relevant to this flow:**

| File | Role in this flow |
|---|---|
| [services/payment-service/app/routes/transfer.py](services/payment-service/app/routes/transfer.py) | Main transfer handler — status transitions |
| [services/payment-service/app/routes/transfer_legacy.py](services/payment-service/app/routes/transfer_legacy.py) | Legacy handler — also sets transfer status |
| [services/payment-service/app/models.py](services/payment-service/app/models.py) | `PaymentTransfer` model — any status-related methods |
| [services/payment-service/app/services/](services/payment-service/app/services/) | Client modules — do any of them affect status? |
| [docs/state-machine-transfer.md](docs/state-machine-transfer.md) | Official state machine documentation |

---

## Task 2.0 — Warm-up
### List All Transfer Statuses in the System
`[~15 min | reading only | no code changes required]`

---

**Your situation:**

You are reviewing the data model before a code review session. A colleague asks: *"What states can a transfer be in?"* You want to answer from the code, not from the documentation — because you know the docs may be out of date.

---

**What to read:**

Open [services/payment-service/app/models.py](services/payment-service/app/models.py) and look at the `PaymentTransfer` model. Read the docstring at the top of the file — it describes the intended status machine. Then open [services/payment-service/app/routes/transfer.py](services/payment-service/app/routes/transfer.py) and read the docstring at the top of the file.

Finally, open [docs/state-machine-transfer.md](docs/state-machine-transfer.md) and read it.

---

**Your tasks:**

1. List every value that the `status` field can hold, based on what you see assigned in the code (not just what the model docstring says).
2. From the code, identify every **terminal status** — a status from which no further transition occurs in normal operation.
3. The `docs/state-machine-transfer.md` file documents the state machine. Compare it to what you found in the code. Do they match?
4. What is the initial status when a transfer record is first created?
5. Are any status values defined as an enum or constant anywhere in the code? Or are they raw string literals assigned inline?

**Expected output:** A list of statuses with classifications (terminal / non-terminal), comparison note, answer to questions 4 and 5.

---

## Task 2.1 — Main Task
### Reconstruct the Complete Status Machine from Code
`[~35 min | code reading + table completion + written output]`

---

**Your situation:**

A new developer joined the team and asked: *"Where can I find the complete list of all transfer states and transitions? I need to understand what can happen to a transfer."*

You have been asked to produce that documentation — from the code, not from any existing docs.

---

**System context:**

In a well-designed system, the state machine for a core entity should be visible in a single authoritative location: either a dedicated module, a class with explicit transition methods, or at minimum a single function where all transitions are made. When transitions are scattered across multiple files, understanding the full state machine requires reading all of them — and no one file gives the complete picture.

---

**What to read:**

Read these files in order, tracking every place where `transfer.status` is assigned a value:
1. [services/payment-service/app/routes/transfer.py](services/payment-service/app/routes/transfer.py)
2. [services/payment-service/app/routes/transfer_legacy.py](services/payment-service/app/routes/transfer_legacy.py)
3. [services/payment-service/app/models.py](services/payment-service/app/models.py)
4. All files in [services/payment-service/app/services/](services/payment-service/app/services/)

---

**Your tasks:**

**Step 1 — Build the complete transition table.**

For every status assignment in the entire payment-service codebase, fill in:

| Status assigned | File | Function/location | Condition that triggers it |
|---|---|---|---|
| `"NEW"` | | | |
| `"DECIDED"` | | | |
| `"POSTED"` | | | |
| `"REJECTED"` | | | |
| `"FAILED"` | | | |

**Step 2 — Count the files.**

How many distinct files contain at least one direct `transfer.status = "..."` assignment? List them.

**Step 3 — Answer the diagnostic questions.**

1. If someone asked you: *"In what ways can a transfer end up with status FAILED?"* — how many separate code paths would you need to trace? Across how many files?
2. Is there a single function, class, or module that serves as the authoritative state machine? If not, describe what that means for a developer who needs to add a new terminal state.
3. What is the risk of having status transition logic scattered across multiple files? Give a concrete example of a bug this pattern could produce.

**Step 4 — Draw the state machine.**

Based on your findings, draw the complete state machine as a diagram or as a structured list. Use this format:

```
[Initial state] NEW
  → DECIDED     condition: decision-hub returned APPROVE or CHALLENGE
  → REJECTED    condition: [your answer]
  → FAILED      condition: [your answer]

[From DECIDED]
  → POSTED      condition: [your answer]
  → FAILED      condition: [your answer]
```

---

## Task 2.2 — Main Task
### Find Every Place That Sets `transfer.status`
`[~25 min | grep-level code search + written analysis]`

---

**Your situation:**

A developer says: *"All status transitions are in transfer.py — just look at the `_log_transition` calls."*

You know that `_log_transition` only logs a transition that already happened. It does not set the status. You need to find every actual status mutation — every line where `transfer.status` is assigned — not every log line.

---

**What to do:**

Search the entire `payment-service` codebase for every occurrence of `transfer.status =`. Include:
- Direct assignments: `transfer.status = "VALUE"`
- Indirect mutations: method calls on a `PaymentTransfer` object that update `status` inside the method

---

**Your tasks:**

**Step 1 — Build the exhaustive assignment list.**

For every location where `transfer.status` is assigned or modified, record:

```
FILE : LINE_APPROXIMATE : transfer.status = "VALUE"
```

Example format:
```
services/payment-service/app/routes/transfer.py : ~123 : transfer.status = "NEW"
```

List every occurrence you find.

**Step 2 — Check for indirect mutations.**

Open [services/payment-service/app/models.py](services/payment-service/app/models.py). Are there any methods on the `PaymentTransfer` class that assign `self.status`? If yes, list them and identify which callers use them.

**Step 3 — Answer the impact questions.**

1. How many distinct files contain at least one status mutation?
2. If you needed to add a new status (for example, `"PENDING_REVIEW"` for transfers flagged by a CHALLENGE decision), in how many places would you need to make changes? List each one.
3. What is the name of the anti-pattern this represents? What is the correct solution?

---

## Task 2.3 — Senior Task
### Source of Truth and State Divergence
`[~35 min | failure scenario analysis + architectural assessment]`

---

**Your situation:**

A production incident report arrives. It states:

> *"We have a transfer where `payment_transfers.status = 'DECIDED'` but there is a corresponding record in `ledger_postings` showing a successful posting. This means the ledger posted successfully, but the transfer status was never updated to `POSTED`. The client sees the transfer as still pending."*

You have been asked to determine how this is possible and what the correct fix is.

---

**System context:**

In payment-service, the transition from `DECIDED` to `POSTED` (or `FAILED`) involves:
1. Calling ledger-mock
2. Processing the ledger response
3. Updating `transfer.status`
4. Committing to the database

Each of these is a distinct operation. A failure between any two steps can leave the system in an inconsistent state.

---

**What to read:**

Open [services/payment-service/app/routes/transfer.py](services/payment-service/app/routes/transfer.py) and find the section that handles the ledger call and the subsequent status update. Read it carefully — count every `await db.commit()` call in the handler and understand exactly what state is persisted at each commit point.

---

**Your tasks:**

**Step 1 — Trace the DECIDED → POSTED code path.**

From the point where the ledger-mock response is received successfully, trace every operation until the `POSTED` status is committed to the database. List each step and identify: at what point is the `transfer.status = "POSTED"` assignment made, and at what point is it committed?

**Step 2 — Find the failure window.**

Is it possible for the following sequence to occur?
1. Ledger-mock successfully creates a posting record in `ledger_postings`
2. Payment-service receives the success response
3. The system fails (exception, network issue, process crash) before `transfer.status = "POSTED"` is committed

Describe exactly what failure would need to occur, and at what point in the code.

**Step 3 — Assess the client-visible consequence.**

If the above scenario occurs, what does the client observe when they call `GET /p2p/transfers/{transfer_id}`? What status do they see? Is money actually moved? Is the discrepancy visible from the API alone?

**Step 4 — Propose the architectural fix.**

Describe in 3–5 sentences the correct approach to prevent this divergence. Consider: a single atomic database transaction, a saga pattern with explicit compensation, or another approach. Your recommendation must tie to what you observed in the code — not a generic pattern description.

---

---

# FLOW 3: DECISION LOGIC / SERVICE OWNERSHIP

**Analytical objective:** Identify every place in the system where business decisions (about whether a transfer is allowed) are made. Verify whether decision logic is correctly centralized in decision-hub or whether it has leaked into other services. Assess audit trail completeness.

**Files relevant to this flow:**

| File | Role in this flow |
|---|---|
| [services/decision-hub/app/db/migrations/versions/002_seed_rules.py](services/decision-hub/app/db/migrations/versions/002_seed_rules.py) | Seeded rules — the canonical rule definitions |
| [services/decision-hub/app/engine/rule_engine.py](services/decision-hub/app/engine/rule_engine.py) | Rule evaluation logic |
| [services/decision-hub/app/routes/evaluate.py](services/decision-hub/app/routes/evaluate.py) | Evaluation endpoint — when is audit written? |
| [services/decision-hub/app/routes/admin.py](services/decision-hub/app/routes/admin.py) | Admin endpoint — rule management |
| [services/payment-service/app/routes/transfer.py](services/payment-service/app/routes/transfer.py) | TO-BE flow — calls decision-hub |
| [services/payment-service/app/routes/transfer_legacy.py](services/payment-service/app/routes/transfer_legacy.py) | AS-IS flow — inline decision logic |
| [contracts/decision-hub.openapi.yaml](contracts/decision-hub.openapi.yaml) | Audit endpoint contract |

---

## Task 3.0 — Warm-up
### Inventory All Decision Rules in the System
`[~15 min | reading only | no code changes required]`

---

**Your situation:**

A compliance auditor asks: *"What business rules does your system enforce? I need a complete list with the thresholds and who owns each rule."*

You have been asked to produce this list from the codebase.

---

**What to read:**

Open [services/decision-hub/app/db/migrations/versions/002_seed_rules.py](services/decision-hub/app/db/migrations/versions/002_seed_rules.py). This migration seeds the initial rule set. Read it carefully.

Then open [contracts/decision-hub.openapi.yaml](contracts/decision-hub.openapi.yaml) and find the endpoint that returns the live rule list.

---

**Your tasks:**

1. Fill in the following table for every rule defined in the seed migration:

| `rule_id` | What it checks | Threshold / blocked values | `action` | `owner` | `priority` |
|---|---|---|---|---|---|
| | | | | | |

2. What API endpoint would you call to get the current **live** state of the rules (accounting for any PATCH updates made after the initial seed)?

3. The seed migration defines rules at database initialization time. If a rule was changed via the admin PATCH endpoint after deployment, the migration's hardcoded values would no longer reflect the live state. In that case, what is the authoritative source of truth for the current rule set?

4. Rules evaluate in priority order. If `LIMIT_DAILY` fires, does evaluation continue to `AML_102`? Read [services/decision-hub/app/engine/rule_engine.py](services/decision-hub/app/engine/rule_engine.py) for the answer.

**Expected output:** Completed rule table, answers to questions 2–4.

---

## Task 3.1 — Main Task
### Identify All Decision Points and Check Audit Coverage
`[~35 min | code reading + table completion + written analysis]`

---

**Your situation:**

A compliance officer has filed an incident report. It reads:

> *"We received a request to audit all transfers to country IR (Iran) made last month. We queried the `decision_audit` table in decision-hub. The table shows significantly fewer records than the `payment_transfers` table for those transactions. Some rejections appear in `payment_transfers` but have no corresponding entry in `decision_audit`. We cannot determine which rule blocked those transfers or who owns the decision."*

You have been asked to investigate. The engineering team tells you: *"The system is working correctly — all transfers to IR are rejected."* But the audit table disagrees with that characterization.

---

**System context:**

In the intended architecture, every transfer rejection flows through decision-hub, which writes an immutable record to `decision_audit`. This record contains the full input context, every rule evaluated (matched or not), the final decision, and the risk score. This is the mechanism that makes decisions explainable and auditable.

If a transfer is rejected without calling decision-hub, no `decision_audit` record is written. The rejection is visible in `payment_transfers` but cannot be explained, traced to a rule, or attributed to a business owner.

---

**What to read:**

| File | What to look for |
|---|---|
| [services/payment-service/app/routes/transfer.py](services/payment-service/app/routes/transfer.py) | Every place where `transfer.status = "REJECTED"` is assigned |
| [services/payment-service/app/routes/transfer_legacy.py](services/payment-service/app/routes/transfer_legacy.py) | Does this also set REJECTED? Is there a decision-hub call? |
| [services/decision-hub/app/routes/evaluate.py](services/decision-hub/app/routes/evaluate.py) | When is `decision_audit` written? Is it always written on rejection? |
| [services/decision-hub/app/db/migrations/versions/002_seed_rules.py](services/decision-hub/app/db/migrations/versions/002_seed_rules.py) | What is the official country blocklist in AML_102? |
| [contracts/decision-hub.openapi.yaml](contracts/decision-hub.openapi.yaml) | The `GET /decision/audit/{decision_id}` endpoint |

---

**Your tasks:**

**Step 1 — Map all rejection paths.**

List every code path in the system that results in a transfer being set to `status = "REJECTED"`. For each path:

| Code path | File | Decision-hub called? | `decision_audit` written? | `decision_id` in response? | `rule_id` in response? |
|---|---|---|---|---|---|
| | | | | | |

**Step 2 — Identify the audit gap.**

If you found a rejection path that does **not** write to `decision_audit`, answer:
- What information is permanently lost for transfers rejected via this path?
- Which of the following compliance questions cannot be answered from the audit table for these transfers?
  - *"Which rule blocked this transfer?"*
  - *"Who is the business owner of that rule?"*
  - *"What version of the rule was active at the time?"*
  - *"Were other rules also evaluated? What did they return?"*
- What is the risk score for these transfers? Where would a regulator look for it?

**Step 3 — Identify the ownership violation.**

In the intended architecture, which single service is the designated owner of all transfer-allow/reject decisions? Is that the case in the current implementation? If not, describe the violation.

**Step 4 — Propose the correct fix.**

Describe in 3–5 sentences what the correct implementation must look like. Be specific: what must change in payment-service, and what must the result be in terms of `decision_audit` coverage for all rejection paths.

---

## Task 3.2 — Main Task
### Rule Ownership and Changeability
`[~25 min | code reading + API analysis + written output]`

---

**Your situation:**

The fincontrol team calls the engineering department at 09:00. They say: *"We need to lower the daily transfer limit from 10,000,000 to 5,000,000 KZT immediately. How long will it take?"*

The engineer on duty says: *"Give me 5 minutes."*

The compliance officer is surprised — they expected it would take days (code review, testing, deployment). Your job is to explain why it takes 5 minutes — and then to find where that guarantee breaks down.

---

**What to read:**

| File | What to look for |
|---|---|
| [services/decision-hub/app/routes/admin.py](services/decision-hub/app/routes/admin.py) | The PATCH endpoint implementation |
| [contracts/decision-hub.openapi.yaml](contracts/decision-hub.openapi.yaml) | PATCH contract, example request body |
| [services/decision-hub/app/db/migrations/versions/002_seed_rules.py](services/decision-hub/app/db/migrations/versions/002_seed_rules.py) | The `LIMIT_DAILY` rule — current threshold |
| [services/payment-service/app/routes/transfer.py](services/payment-service/app/routes/transfer.py) | Does payment-service have any hardcoded numeric limits? |

---

**Your tasks:**

1. Write the exact `curl` command that would lower the `LIMIT_DAILY` threshold from 10,000,000 to 5,000,000. Use the OpenAPI spec to construct the request body.

2. After sending the PATCH request, how quickly does the change take effect for new transfer evaluations? Does the service need to restart? How do you know from the code?

3. Read [services/payment-service/app/routes/transfer.py](services/payment-service/app/routes/transfer.py) carefully. Is there any hardcoded numeric value or string constant related to transfer limits or country restrictions? If yes, quote it exactly.

4. If the same limit threshold exists in two places (once in decision-hub's rule database, once hardcoded in payment-service) with different values, describe the operational consequence with a specific example. Use concrete amounts (e.g., a transfer of 9,500,000 KZT).

5. Who is the accountable business owner of the hardcoded value in payment-service, according to the code? How would you find them in a real organization?

---

## Task 3.3 — Senior Task
### Explainability Comparison: TO-BE vs AS-IS
`[~40 min | comparative analysis + SQL + written output]`

---

**Your situation:**

A customer calls the bank. They say: *"My transfer was rejected yesterday and I don't understand why. Can you tell me what the reason was?"*

The customer service agent has the `transfer_id`. Your job is to determine what information the agent can retrieve — and whether the two available endpoints (`/p2p/transfer-legacy` and `/p2p/transfer`) provide equally useful answers.

---

**What to read:**

| File | Role |
|---|---|
| [services/payment-service/app/routes/transfer_legacy.py](services/payment-service/app/routes/transfer_legacy.py) | AS-IS rejection path — response structure |
| [services/payment-service/app/routes/transfer.py](services/payment-service/app/routes/transfer.py) | TO-BE rejection path — response structure |
| [services/decision-hub/app/routes/evaluate.py](services/decision-hub/app/routes/evaluate.py) | What `decision_audit` contains |
| [contracts/decision-hub.openapi.yaml](contracts/decision-hub.openapi.yaml) | `GET /decision/audit/{decision_id}` endpoint |

---

**Your tasks:**

**Part A — AS-IS explainability:**

1. A transfer was rejected via the legacy endpoint. What fields are present in the rejection response? List every field.
2. What information is **not** available in the response or in the database for a legacy-rejected transfer? Be specific.
3. The agent asks: *"Which rule blocked this transfer?"* Can they answer this from the AS-IS path? What would they find if they searched the database?

**Part B — TO-BE explainability:**

1. The same transfer was rejected via the TO-BE endpoint. What fields are present in the rejection response? List every field, including nested ones.
2. The agent now calls `GET /decision/audit/{decision_id}`. What additional information is available that was not in the original response?
3. The agent asks: *"Were any other rules evaluated? What did they return?"* Can they answer this? From which data source and which field?

**Part C — Comparative assessment:**

Build a comparison table:

| Question the agent needs to answer | Answerable from AS-IS? | Answerable from TO-BE? | Source in TO-BE |
|---|---|---|---|
| Which rule blocked this transfer? | | | |
| Who owns that rule? | | | |
| What version of the rule was active? | | | |
| What was the risk score? | | | |
| Were other rules evaluated? | | | |
| What was the exact input context? | | | |

**Part D — Architectural conclusion:**

In 3 sentences: what structural difference between the two paths produces this difference in explainability? What would need to change in the AS-IS path to make it equally auditable?

---

---

# FLOW 4: OBSERVABILITY / TRACING / RCA

**Analytical objective:** Verify that `X-Correlation-Id` is correctly propagated across all inter-service calls. Identify any gap in the propagation chain. Demonstrate how to use correlation IDs, logs, and database records to reconstruct a failed transfer's complete lifecycle.

**Files relevant to this flow:**

| File | Role in this flow |
|---|---|
| [shared/correlation.py](shared/correlation.py) | Correlation ID middleware and ContextVar |
| [shared/logging.py](shared/logging.py) | JSON structured logger |
| [services/api-gateway/app/main.py](services/api-gateway/app/main.py) | Correlation ID generation and forwarding |
| [services/payment-service/app/services/decision_client.py](services/payment-service/app/services/decision_client.py) | Headers sent to decision-hub |
| [services/payment-service/app/services/ledger_client.py](services/payment-service/app/services/ledger_client.py) | Headers sent to ledger-mock |
| [services/decision-hub/app/routes/evaluate.py](services/decision-hub/app/routes/evaluate.py) | How decision-hub uses correlation_id |
| [services/ledger-mock/app/main.py](services/ledger-mock/app/main.py) | How ledger-mock logs with correlation_id |

---

## Task 4.0 — Warm-up
### Trace Where X-Correlation-Id Is Generated and Stored
`[~15 min | reading only | no code changes required]`

---

**Your situation:**

Before conducting an RCA, you need to understand how request tracing works in this system. Your starting point is to find where the correlation ID originates and how it flows through the system.

---

**What to read:**

Open [shared/correlation.py](shared/correlation.py) and read the full file. Then open [services/api-gateway/app/main.py](services/api-gateway/app/main.py) and find where `CorrelationMiddleware` is instantiated. Finally, open [shared/logging.py](shared/logging.py) and see how the correlation ID appears in log output.

---

**Your tasks:**

1. Which service generates the `X-Correlation-Id` if the client does not provide one? How do you know this from the code?
2. What Python mechanism stores the correlation ID so that any log call within the same request context can access it without it being passed as a function argument?
3. The `CorrelationMiddleware` is instantiated with different parameters in different services. What parameter differs between api-gateway and payment-service? What is the effect of that difference?
4. In what HTTP response headers does the correlation ID appear, based on the code?
5. Look at [shared/logging.py](shared/logging.py). How does the `JSONFormatter` include the `correlation_id` in every log line? Is it passed explicitly to each log call?

**Expected output:** Short answers to each question. No code changes.

---

## Task 4.1 — Main Task
### Correlation-Id Propagation: Trace Across All Service Calls
`[~30 min | code reading + table completion + written analysis]`

---

**Your situation:**

A customer filed a complaint about a failed transfer. You have the `X-Correlation-Id` from the client's request headers. You need to determine whether you can use this ID to find relevant log entries in every service that processed this request.

Before you can trust the logs, you need to verify that the correlation ID was actually forwarded correctly across every inter-service call.

---

**What to read:**

| File | What to look for |
|---|---|
| [services/api-gateway/app/main.py](services/api-gateway/app/main.py) | How headers are built and forwarded |
| [services/payment-service/app/services/decision_client.py](services/payment-service/app/services/decision_client.py) | What headers are sent to decision-hub |
| [services/payment-service/app/services/ledger_client.py](services/payment-service/app/services/ledger_client.py) | What headers are sent to ledger-mock |
| [services/decision-hub/app/routes/evaluate.py](services/decision-hub/app/routes/evaluate.py) | How decision-hub receives and uses the correlation_id |
| [services/ledger-mock/app/main.py](services/ledger-mock/app/main.py) | How ledger-mock receives and logs the correlation_id |

---

**Your tasks:**

**Step 1 — Map the propagation chain.**

For each inter-service call, complete the following table:

| Hop | Sent by | How (header name / body field) | Received by | How received | Does the service log it? |
|---|---|---|---|---|---|
| Client → api-gateway | client | `X-Correlation-Id` header | api-gateway | CorrelationMiddleware | yes |
| api-gateway → payment-service | | | | | |
| payment-service → decision-hub | | | | | |
| payment-service → ledger-mock | | | | | |

**Step 2 — Identify forwarding method.**

For each hop where the **sender** is payment-service: is the correlation ID forwarded as an HTTP header, embedded in the request body, or both? Is this consistent across all outbound calls?

**Step 3 — Detect any gap.**

Is there any inter-service call where the `X-Correlation-Id` is **not** forwarded as an HTTP header to the receiving service? If yes:
- Which hop is affected?
- What does the receiving service log as its `correlation_id` for that call?
- If you run `docker compose logs | grep "YOUR_CORRELATION_ID"`, would you expect to find matching entries in that service's logs?

**Step 4 — Assess tracing completeness.**

Based on your findings: can an engineer reconstruct the complete lifecycle of a specific request across all four services using a single `correlation_id`? Are there any services where entries would be missing?

---

## Task 4.2 — Main Task
### RCA Simulation: Reconstruct a Failed Transfer
`[~30 min | SQL query design + log analysis + diagnostic reasoning]`

---

**Your situation:**

A support ticket arrives with the following information:

> *"Transfer failed. The client attempted at approximately 14:00 today. Amount: 50,000 KZT. Destination: country KZ. device_trust: HIGH. The client says they saw an error but does not know if money was deducted."*

You do not know yet whether the transfer was rejected by a rule, failed at the decision-hub, or failed at the ledger. Your job is to reconstruct exactly what happened and produce a clear RCA.

---

**System context:**

You have access to:
- The `payment_transfers` table in the payment-service database
- The `decision_audit` table in the decision-hub database
- The `ledger_postings` table in the ledger-mock database
- Structured JSON logs from all services (searchable by `correlation_id`)

---

**Your tasks:**

**Step 1 — Design the diagnostic query sequence.**

Write the SQL queries you would run, in order, to reconstruct the full transfer lifecycle. Start from the `payment_transfers` table and work outward:

```sql
-- Query 1: Find the transfer record
SELECT ...

-- Query 2: If decision_id is not null, check decision_audit
SELECT ...

-- Query 3: Check ledger_postings
SELECT ...
```

For each query, explain what you are looking for and what the result tells you.

**Step 2 — Build the diagnostic decision tree.**

For each possible final `status` value in `payment_transfers`, describe what it means, whether money moved, and what your next diagnostic step would be:

| `status` | What it means | Did money move? | Next diagnostic step |
|---|---|---|---|
| `REJECTED` | | | |
| `FAILED` | | | |
| `DECIDED` | | | |
| `POSTED` | | | |

**Step 3 — Distinguish failure types.**

1. The transfer is `status = FAILED` and `decision_id` is **not null**. What does this tell you about where in the flow the failure occurred? What was the last successful step?
2. The transfer is `status = FAILED` and `decision_id` **is null**. What does this tell you about the failure location?
3. What specific `event` field value in the structured logs would confirm the exact failure reason in each case?

---

## Task 4.3 — Senior Task
### Find the Observability Gap
`[~35 min | code audit + test design + impact assessment]`

---

**Your situation:**

The engineering team presents a claim during an architecture review: *"We have full end-to-end observability. Every request can be traced using the correlation ID across all services."*

You have been asked to audit this claim and produce a written assessment of whether it is accurate.

---

**What to read:**

| File | What to audit |
|---|---|
| [services/payment-service/app/services/decision_client.py](services/payment-service/app/services/decision_client.py) | `X-Correlation-Id` in outbound headers |
| [services/payment-service/app/services/ledger_client.py](services/payment-service/app/services/ledger_client.py) | `X-Correlation-Id` in outbound headers |
| [shared/correlation.py](shared/correlation.py) | How `generate_if_missing=True` affects ledger-mock |

---

**Your tasks:**

**Step 1 — Audit each outbound call.**

For each HTTP call made by payment-service, check whether the `X-Correlation-Id` header is correctly forwarded. Specifically: is the original `correlation_id` value forwarded, or is a **new** value generated in its place?

| Call | `X-Correlation-Id` forwarded? | Original value used or new generated? |
|---|---|---|
| payment-service → decision-hub | | |
| payment-service → ledger-mock | | |

**Step 2 — Describe the gap's consequences.**

If there is a hop where the original correlation ID is **not** forwarded:
1. What value does the receiving service log as `correlation_id` in its own log entries?
2. If you search `docker compose logs | grep "ORIGINAL_CORRELATION_ID"`, will the affected service's logs appear in the results?
3. What is the practical consequence for an engineer conducting an incident investigation that involves a failure at that service?

**Step 3 — Design a verification test.**

Describe a test you could run to verify or disprove the claim that correlation propagation is end-to-end complete. Your test must include:
- The exact `curl` command you would send
- What specific log entries you would search for
- How you would confirm that the same ID appears in all four services' logs
- What a failing result would look like

**Step 4 — Assess the incident response impact.**

If this gap exists in production and a high-severity incident occurs involving a ledger failure: what specific investigation capability does the team lose? How does this affect the time to resolution?

---

---

# FLOW 5: API CONTRACTS VS RUNTIME BEHAVIOR

**Analytical objective:** Compare the OpenAPI contract documentation against the actual runtime behavior of the code. Identify fields, response codes, and behaviors that are documented but not implemented, implemented but not documented, or documented incorrectly.

**Files relevant to this flow:**

| File | Role in this flow |
|---|---|
| [contracts/payment-service.openapi.yaml](contracts/payment-service.openapi.yaml) | Payment-service API contract |
| [contracts/decision-hub.openapi.yaml](contracts/decision-hub.openapi.yaml) | Decision-hub API contract |
| [contracts/ledger-mock.openapi.yaml](contracts/ledger-mock.openapi.yaml) | Ledger-mock API contract |
| [services/payment-service/app/routes/transfer.py](services/payment-service/app/routes/transfer.py) | Actual response construction |
| [services/decision-hub/app/routes/evaluate.py](services/decision-hub/app/routes/evaluate.py) | Actual `EvaluateRequest` Pydantic model |
| [services/api-gateway/app/main.py](services/api-gateway/app/main.py) | Which headers are forwarded |

---

## Task 5.0 — Warm-up
### Map All Documented Endpoints to Code Handlers
`[~15 min | reading only | no code changes required]`

---

**Your situation:**

You are starting an API audit. Before comparing contracts to runtime behavior, you need a complete inventory of what endpoints exist — both in the documentation and in the code.

---

**What to read:**

Open all four OpenAPI specs in [contracts/](contracts/) and list every path. Then open the corresponding route files in each service and list every registered endpoint.

---

**Your tasks:**

1. Complete the following endpoint inventory table:

| Method + Path | Service | In OpenAPI spec? | Code handler file |
|---|---|---|---|
| `POST /p2p/transfer` | payment-service | | |
| `POST /p2p/transfer-legacy` | payment-service | | |
| `GET /p2p/transfers/{transfer_id}` | payment-service | | |
| `POST /decision/evaluate` | decision-hub | | |
| `GET /decision/rules` | decision-hub | | |
| `PATCH /decision/rules/{rule_id}` | decision-hub | | |
| `GET /decision/audit/{decision_id}` | decision-hub | | |
| `POST /ledger/posting` | ledger-mock | | |
| `GET /health` | all services | | |

2. Is there any endpoint in the code that is **not** documented in the OpenAPI spec?
3. Is there any endpoint in the OpenAPI spec that does **not** have a corresponding code handler?

**Expected output:** Completed table, answers to questions 2 and 3.

---

## Task 5.1 — Main Task
### Verify Response Schemas Against Actual Code Behavior
`[~35 min | contract vs code comparison + table completion]`

---

**Your situation:**

A frontend team is integrating with the payment API. They are using the OpenAPI contract in [contracts/payment-service.openapi.yaml](contracts/payment-service.openapi.yaml) as their single source of truth. They will write client code that handles every documented response code and expects every documented field.

You have been asked to verify whether the contract accurately describes what the API actually does.

---

**What to read:**

| File | What to look for |
|---|---|
| [contracts/payment-service.openapi.yaml](contracts/payment-service.openapi.yaml) | Response codes, schemas, enum values |
| [services/payment-service/app/routes/transfer.py](services/payment-service/app/routes/transfer.py) | What the handler actually returns — every `return` and `raise HTTPException` |
| [services/payment-service/app/routes/transfer_legacy.py](services/payment-service/app/routes/transfer_legacy.py) | What the legacy handler returns |

---

**Your tasks:**

**Step 1 — Verify response status codes for `POST /p2p/transfer`.**

| HTTP Status | Documented in OpenAPI? | Can the code actually return it? | Under what condition? |
|---|---|---|---|
| `200` | | | |
| `400` | | | |
| `409` | | | |
| `422` | | | |
| `503` | | | |

**Step 2 — Verify the `status` field enum.**

The `TransferResponse` schema documents the `status` field with these enum values: `POSTED`, `REJECTED`, `FAILED`, `DECIDED`.

- Can the API ever return `status = "DECIDED"` in the response body of `POST /p2p/transfer`? Trace the code carefully.
- `DECIDED` is a real status in the `payment_transfers` table. Does it ever appear in an API response? Why or why not?

**Step 3 — Verify the GET endpoint response schema.**

Open the OpenAPI spec and find the documented response schema for `GET /p2p/transfers/{transfer_id}`. Then open the handler in `transfer.py` and look at what the `get_transfer()` function actually returns.

- Is there a documented response schema in the OpenAPI spec for this endpoint?
- List every field that `get_transfer()` actually returns in the response body.
- Is the OpenAPI schema complete?

**Step 4 — Identify undocumented behavior.**

Based on Steps 1–3, identify at least one documented response code or field that the code **never actually produces** in practice, and at least one behavior the code produces that is **not documented** in the spec.

---

## Task 5.2 — Main Task
### Find Undocumented and Misdocumented Behavior
`[~30 min | contract-to-code comparison + written assessment]`

---

**Your situation:**

The team is preparing to publish the API specification to external partners. You have been asked to do a final review. Your goal is to find anything in the spec that would cause a developer — who reads the spec but has not seen the code — to build incorrect assumptions or implement error handling that never triggers.

---

**What to read:**

| File | What to look for |
|---|---|
| [contracts/decision-hub.openapi.yaml](contracts/decision-hub.openapi.yaml) | `EvaluateRequest` schema — `required` array |
| [services/decision-hub/app/routes/evaluate.py](services/decision-hub/app/routes/evaluate.py) | `EvaluateRequest` Pydantic model — is `correlation_id` required? |
| [contracts/payment-service.openapi.yaml](contracts/payment-service.openapi.yaml) | Header documentation — is `X-Fail-Mode` listed? |
| [services/api-gateway/app/main.py](services/api-gateway/app/main.py) | `_FORWARD_HEADERS` — which headers are forwarded |

---

**Your tasks:**

**Issue 1 — `correlation_id` required vs optional:**

1. Open [contracts/decision-hub.openapi.yaml](contracts/decision-hub.openapi.yaml). Find the `EvaluateRequest` schema. Is `correlation_id` listed in the `required` array?
2. Open [services/decision-hub/app/routes/evaluate.py](services/decision-hub/app/routes/evaluate.py). Find the `EvaluateRequest` Pydantic model definition. Is `correlation_id` required or optional in the Python model?
3. What happens at runtime if payment-service sends a request without `correlation_id`? Does decision-hub reject the request or accept it?
4. Is this a contract violation? Who is correct — the schema or the code?

**Issue 2 — `X-Fail-Mode` header documentation:**

1. Is `X-Fail-Mode` documented in [contracts/api-gateway.openapi.yaml](contracts/api-gateway.openapi.yaml)? In [contracts/payment-service.openapi.yaml](contracts/payment-service.openapi.yaml)?
2. Which services actually process this header? Trace its path through the chain.
3. Which service should be responsible for documenting a header — the service that first receives it from a client, or the service that ultimately uses it?

**Issue 3 — Idempotent replay response code:**

1. What HTTP status code does `POST /p2p/transfer` return when a duplicate `Idempotency-Key` is detected?
2. What HTTP status code would a developer expect if they read only the OpenAPI spec and saw the documented response codes?
3. Is HTTP 409 (Conflict) documented for this endpoint? If a developer sees 409 documented, what behavior would they implement in their client?
4. What is the semantically correct HTTP response for a successfully replayed idempotent request — 200 with `idempotent: true`, or 409? Explain your reasoning.

**Written assessment:**

Write a 3-paragraph assessment for the team:
- Paragraph 1: Which findings would **block** external partner integration
- Paragraph 2: Which findings would create **incorrect assumptions** but not hard failures
- Paragraph 3: Which findings are **informational gaps** with no functional impact

---

## Task 5.3 — Senior Task
### Contract-First Discipline Audit
`[~40 min | comprehensive drift inventory + process recommendation]`

---

**Your situation:**

You are writing a recommendation for the engineering team on how to prevent API contract drift in the future. Before making recommendations, you need to document all the drift you found in Flows 5.0, 5.1, and 5.2 and classify it systematically.

---

**Your tasks:**

**Step 1 — Build the complete drift inventory.**

Compile all contract divergences you found across Tasks 5.0–5.2. For each, fill in:

| Drift | What the contract says | What the code does | Severity | Direction of fix |
|---|---|---|---|---|
| | | | | |

Use these severity classifications:
- **BREAKING:** A client built against the contract would experience a hard failure
- **MISLEADING:** A client would build incorrect assumptions and write wrong error handling
- **INFORMATIONAL:** Documentation is missing or incomplete, but there is no functional impact on a well-implemented client

**Step 2 — Classify the failure mode.**

For each BREAKING or MISLEADING drift, determine:
- Was this a **documentation-first failure** (code was changed after the contract was written, and the contract was not updated)?
- Or an **implementation-first failure** (the contract was written to describe intended behavior, but the code diverged during implementation)?

**Step 3 — Process recommendation.**

Recommend one or more process changes that would prevent contract drift. Your recommendations must:
- Tie directly to at least one specific drift you found (not generic advice)
- Be realistic for a small team
- Address both the detection and the prevention of drift

Consider: OpenAPI validation in CI, Pydantic schema export and comparison, contract testing with tools like Dredd or Schemathesis, or a manual review checklist. Pick what fits this team's scale and explain your reasoning.

---

---

# QUESTION BANK (Step 6)

The following questions are designed for use in one-on-one grading sessions. They do not have answers provided. Each question maps directly to observable behavior in this codebase.

---

## CR — Code Reading

**CR-1.** The `_log_transition()` function in [services/payment-service/app/routes/transfer.py](services/payment-service/app/routes/transfer.py) accepts `**extra` as a parameter. What Python language feature does this represent? What is the purpose of using it here rather than explicit named parameters? Give an example of how it is called.
*(Layer 1: processing logic)*

**CR-2.** Trace the complete execution of a `POST /p2p/transfer` request from the moment it arrives at api-gateway to the moment a response is returned to the client. List every function call in order, including cross-service HTTP calls, and name the file where each function lives.
*(Layer 1: processing logic)*

**CR-3.** Both `decision_client.py` and `ledger_client.py` use `httpx.AsyncClient` as a context manager (`async with httpx.AsyncClient(...) as client:`). What happens if the remote service returns HTTP 500? What exception is raised by `response.raise_for_status()`? Where is this exception caught?
*(Layer 1: processing logic)*

**CR-4.** In [services/decision-hub/app/engine/rule_engine.py](services/decision-hub/app/engine/rule_engine.py), the `run_evaluation()` function breaks out of the loop on the first `REJECT` match. What is the stated reasoning for this design choice? What does it mean for the order in which rules must be defined?
*(Layer 1: processing logic)*

**CR-5.** `CorrelationMiddleware` is instantiated with `generate_if_missing=True` in api-gateway and `generate_if_missing=False` in payment-service. Explain the design intent behind this difference. What happens if a request reaches payment-service directly (not through api-gateway) without an `X-Correlation-Id` header?
*(Layer 1 / Layer 4)*

---

## BL — Business Logic

**BL-1.** Compare the rejection response from `POST /p2p/transfer-legacy` (AS-IS) and `POST /p2p/transfer` (TO-BE) for a transfer to country IR. List every field present in each response. What information is available in TO-BE that is completely absent in AS-IS?
*(Layer 1 / Layer 6)*

**BL-2.** The `FRAUD_017` rule has `action: "REJECT"`. If the risk team wanted to add a new rule that flags transfers above 500,000 KZT for manual review without blocking them, what `action` value would be used? What would change in the engine's evaluation behavior for such a rule?
*(Layer 1)*

**BL-3.** Compliance wants a new rule: *"Reject if amount > 5,000,000 AND country = RU."* Which `condition_type` would this rule use? Is it currently supported by `rule_engine.py`? If yes, write the `condition_params` JSON. If no, what change to the engine would be required?
*(Layer 1)*

**BL-4.** A transfer is submitted with the following values: `country="IR"`, `amount=50000`, `currency="KZT"`, `device_trust="HIGH"`, `daily_sum=0`. Trace the complete evaluation in decision-hub: which rule fires, at what priority, what is the final decision, and what `risk_score` is returned?
*(Layer 1 / Layer 2)*

---

## DS — Data / State

**DS-1.** Draw the complete transfer status machine as it exists in the actual code — not the documentation. Include every state, every transition, and the condition that triggers each transition. How many distinct terminal states exist?
*(Layer 2)*

**DS-2.** The `PaymentTransfer` model has a `decision_id` column. When exactly is this column populated? What value does it hold for: (a) a REJECTED transfer, (b) a POSTED transfer, (c) a FAILED transfer where decision-hub was unreachable?
*(Layer 2)*

**DS-3.** `PaymentIdempotency` stores a `response_snapshot`. List all the code paths in `create_transfer()` that write a record to this table. Are there any paths through the handler where a `PaymentTransfer` record is created but **no** corresponding `PaymentIdempotency` record is written?
*(Layer 2)*

**DS-4.** Payment-service uses `Idempotency-Key` (client-provided) for its deduplication. Ledger-mock uses `transfer_id` (payment-service-generated) for its deduplication. Why are two different keys used at two different layers? What failure mode does each key protect against?
*(Layer 2 / Layer 4)*

**DS-5.** Describe a specific sequence of events where a `decision_audit` record exists in decision-hub but the corresponding `payment_transfers` record has `decision_id = NULL`. Under what conditions does this divergence occur?
*(Layer 2 / Layer 5)*

---

## AC — API / Contracts

**AC-1.** Open [contracts/payment-service.openapi.yaml](contracts/payment-service.openapi.yaml) and list all documented response codes for `POST /p2p/transfer`. Then read the handler in `transfer.py` and list all HTTP status codes the handler can actually return. Are there undocumented codes? Are there documented codes the handler never returns?
*(Layer 3)*

**AC-2.** The `EvaluateRequest` schema in [contracts/decision-hub.openapi.yaml](contracts/decision-hub.openapi.yaml) lists `correlation_id` in its `required` array. The `EvaluateRequest` Pydantic model in `evaluate.py` defines `correlation_id` as `str | None = None`. Which is correct? What happens at runtime if `correlation_id` is omitted?
*(Layer 3)*

**AC-3.** The OpenAPI spec for `GET /p2p/transfers/{transfer_id}` has no documented response schema (only `description: Transfer details`). Read the `get_transfer()` handler and list every field it includes in the response. What is the API contract problem this creates?
*(Layer 3)*

**AC-4.** `POST /p2p/transfer` returns HTTP `200` for a REJECTED transfer. From a REST design perspective, is this correct? What would an alternative design look like (e.g., HTTP 422)? What are the trade-offs of each approach?
*(Layer 3)*

**AC-5.** The `X-Fail-Mode` header is documented in the payment-service OpenAPI spec but not in the api-gateway spec. Yet api-gateway forwards this header downstream. Who should own the documentation of this header? What is the contract problem if it is documented in the wrong place?
*(Layer 3)*

---

## IR — Idempotency / Retry

**IR-1.** In `create_transfer()`, at what step in the execution sequence is the `PaymentIdempotency` record written? Is this before or after the ledger-mock call? Does the order matter for retry safety?
*(Layer 4)*

**IR-2.** A client's connection drops after the payment-service sets `status=DECIDED` but before the ledger call completes. The client retries with the same `Idempotency-Key`. Trace the full execution of the retry. What response does the client receive? Is money moved twice?
*(Layer 4)*

**IR-3.** The ledger-mock `PostingRequest` body includes a `correlation_id` field. The `ledger_client.py` also sends `X-Correlation-Id` as an HTTP header. If these two values differ, which one does ledger-mock use for its own log entries? Why?
*(Layer 4)*

**IR-4.** Payment-service deduplicates using `Idempotency-Key` (client-provided string). Ledger-mock deduplicates using `transfer_id` (UUID generated by payment-service). Explain why each layer uses a different key, and what would break if ledger-mock used the client's `Idempotency-Key` instead.
*(Layer 4)*

**IR-5.** Can both idempotency mechanisms fail simultaneously — meaning payment-service's idempotency check fires and returns a cached response, while ledger-mock receives the posting request twice and successfully posts twice? Describe the exact sequence of events that would produce this outcome.
*(Layer 4)*

---

## OR — Observability / RCA

**OR-1.** A transfer has `status=FAILED`. You need to determine whether it failed because decision-hub was unreachable, or because ledger-mock failed. How do you distinguish between these two cases using only the `payment_transfers` table and structured logs? What specific fields or events do you use?
*(Layer 5)*

**OR-2.** You have a `correlation_id` from a client complaint. Describe the complete sequence of queries and log searches you would perform to reconstruct the full lifecycle of that request across all four services. What table do you start with? What do you do next if `decision_id` is null?
*(Layer 5)*

**OR-3.** A customer says their transfer was rejected but they do not understand why. They provide their `transfer_id`. Describe the complete steps to retrieve the full audit trail: which table, which field, which API endpoint, and what you would present to the customer.
*(Layer 5)*

**OR-4.** The `_log_transition()` function is called at every status transition. But in a production incident, some transitions are missing from the log stream. Name at least two scenarios that could cause a transition to be executed in the code but not appear in the logs.
*(Layer 5)*

**OR-5.** A colleague claims: *"Correlation ID is propagated everywhere in this system."* Design a test — including the exact `curl` command and log search strategy — that would either confirm or refute this claim. What would a failing result look like?
*(Layer 5)*

---

## AR — Architecture

**AR-1.** The `decision_id` UUID is a key reference between payment-service and decision-hub. Where exactly is this UUID generated? Where is it first stored? How does payment-service get it? Trace the complete lifecycle of this identifier.
*(Layer 6)*

**AR-2.** The api-gateway module docstring states the gateway has *"no business logic."* Read the actual `main.py` code. Is this claim accurate today? What would happen — architecturally — if someone added a country check inside the `_proxy()` function?
*(Layer 6)*

**AR-3.** Both `transfer.py` and `transfer_legacy.py` are registered as active routers in the same payment-service application. What is the stated purpose of keeping the legacy endpoint? Is it appropriate for a production system to expose two competing implementations of the same business operation?
*(Layer 6)*

**AR-4.** Decision-hub provides a `PATCH /decision/rules/{rule_id}` endpoint specifically so business rules can be changed without code deployments. If payment-service contains any hardcoded numeric thresholds or country lists that mirror what the rules define, what is the architectural consequence?
*(Layer 6)*

**AR-5.** `shared/correlation.py` and `shared/logging.py` are used by all four services via a local Python package. As the system grows to 10+ services, what are the risks of this shared-package approach? What alternative architectures exist for cross-cutting concerns like logging and tracing?
*(Layer 6)*

---

## SD — Senior Deep-Dive

**SD-1.** The `run_evaluation()` loop breaks on the first REJECT match. If `AML_102` fires and stops evaluation, does the `decision_audit.rules_checked` field contain an entry for `FRAUD_017`? Trace the code carefully and explain the answer.
*(Layer 1 / Layer 2)*

**SD-2.** Payment-service uses `CorrelationMiddleware` with `generate_if_missing=False`. When a request arrives without `X-Correlation-Id`, what value is stored in the ContextVar? What value appears in the `correlation_id` field of every log line emitted during that request?
*(Layer 4 / Layer 5)*

**SD-3.** Currently, if decision-hub is temporarily unavailable, the transfer is set to `FAILED`. Is this the correct behavior? Design an alternative approach (circuit breaker, retry with backoff, async evaluation queue, or another pattern). For each alternative, describe: what state machine changes are required, what new tables or fields are needed, and what the client experience is.
*(Layer 4 / Layer 6)*

**SD-4.** The `decision_audit` table stores `transfer_context` as a full JSONB snapshot of the input at the time of evaluation. If the `LIMIT_DAILY` threshold is changed from 10,000,000 to 5,000,000 via the PATCH endpoint after a decision is made, and someone replays the original audit record — would they get the same result? What are the implications for audit integrity and regulatory compliance?
*(Layer 2 / Layer 6)*

**SD-5.** The `decision_id` UUID is generated by decision-hub, stored in `decision_audit`, and referenced by payment-service in `payment_transfers.decision_id`. Enumerate every place in the codebase where this UUID is: (a) generated, (b) stored to a database, (c) passed between services, (d) returned to a client. Is there any scenario where a `decision_audit` record exists but `payment_transfers.decision_id` is null for the same logical request?
*(Layer 2 / Layer 5)*

---

## BE — Backend Patterns

**BE-1.** Both `decision_client.py` and `ledger_client.py` create a new `httpx.AsyncClient` instance per request using `async with`. What is the operational trade-off between this approach (new connection per request) versus maintaining a shared persistent client with connection pooling? When does this choice matter in a high-throughput banking context?
*(Layer 4)*

**BE-2.** `shared/correlation.py` uses `ContextVar` rather than a module-level global variable to store the correlation ID. Why is a module-level global variable unsafe in an async FastAPI application where multiple requests are processed concurrently in the same process? Describe what would go wrong if `_correlation_id` were a plain `str` instead of a `ContextVar`.
*(Layer 4)*

**BE-3.** Both client modules call `response.raise_for_status()` after receiving a response. What does this method do? If decision-hub returns HTTP 422 (Unprocessable Entity), what exception is raised, what is its type, and where in `transfer.py` is it caught?
*(Layer 1)*

**BE-4.** `PaymentIdempotency.response_snapshot` is stored as a PostgreSQL `JSONB` column containing the full response body. What are the trade-offs of this approach compared to storing the idempotency result in normalized relational columns? In what scenario does the blob approach behave incorrectly or return stale data?
*(Layer 2)*

**BE-5.** `transfer_id` is a UUID generated by payment-service. `Idempotency-Key` is a string provided by the client. Both exist in the system simultaneously. What is the architectural reason for having both? Which one is the stable, client-facing identifier, and which is the internal reference key?
*(Layer 3)*

**BE-6.** The `PaymentTransfer` model has both `created_at` and `updated_at` timestamp columns. The `PaymentIdempotency` model has only `created_at`. What information would be permanently lost if `PaymentTransfer` also had only `created_at`? Give a specific example of an investigation that requires `updated_at`.
*(Layer 2 / Layer 5)*

**BE-7.** The `run_evaluation()` function currently stops at the first REJECT match and returns immediately. If you changed the behavior to evaluate all rules and collect all REJECT matches (not just the first), what would change in: (a) the `EngineResult` structure, (b) the `decision_audit` record, (c) the API response to the client? Is there a case where this change would alter the final decision?
*(Layer 1)*

**BE-8.** The `decision_audit` table stores `transfer_context` as a snapshot of the input at the time of evaluation. This is a deliberate design choice. Explain why the context is snapshotted rather than stored as a foreign key to the `payment_transfers` table. What property of the audit record does this snapshot guarantee?
*(Layer 2 / Layer 6)*

---

---

# DELIVERABLE FORMAT

For each flow, produce a written analysis document. Your output should be structured, specific, and grounded in code references.

**Format for each task:**

1. **Findings** — What you observed in the code. Reference specific files and functions.
2. **Analysis** — What the finding means for system correctness, auditability, or observability.
3. **Proposed fix** — What the correct implementation should be. Describe behavior, not just "fix the code."

**What makes a strong answer:**
- References specific file paths and function names
- Distinguishes between what the system *appears* to do and what it *actually* does
- Identifies the impact on real operational scenarios (retry safety, compliance, incident response)
- Proposes corrections that address the root cause, not the symptom

**What makes a weak answer:**
- Describes behavior correctly but does not identify the problem
- Identifies a problem but cannot explain its impact
- Proposes a fix (e.g., "add logging") that does not address the structural issue

---

*This assignment is based on a realistic banking system architecture. The problems you are asked to identify are the kinds of problems that appear in production systems — not academic puzzles. Treat your findings as if you would present them to an engineering team making a real decision about whether to ship this system.*
