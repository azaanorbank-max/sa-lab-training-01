# Transfer Status Lifecycle

## State Machine

```
                         ┌─────────────────────────────────┐
                         │                                 │
          ┌──────────────▼───────────────┐                │
  START   │           NEW                │                │
──────────►  (transfer record created)   │                │
          └──┬──────────────┬────────────┘                │
             │              │                             │
             │ hub OK       │ hub unreachable             │
             │ APPROVE or   │ (network error,             │
             │ CHALLENGE     │  timeout)                   │
             │              │                             │
             ▼              ▼                             │
          DECIDED         FAILED ◄───────────────────────┘
          │                                    ledger ERROR
          │                                    or TIMEOUT
          │
          ├─── hub said REJECT ──► REJECTED  (terminal)
          │
          ▼
       DECIDED ──── ledger OK ──────► POSTED   (terminal)
                 └── ledger FAIL ──► FAILED    (terminal)
```

## Transition Table

| From      | To         | Trigger                              | Logged Event              |
|-----------|------------|--------------------------------------|---------------------------|
| —         | NEW        | Transfer request received            | `transfer_created`        |
| NEW       | DECIDED    | Decision hub returned APPROVE/CHALLENGE | `status_transition`    |
| NEW       | REJECTED   | Decision hub returned REJECT         | `status_transition`       |
| NEW       | FAILED     | Decision hub unreachable/timeout     | `status_transition`       |
| DECIDED   | POSTED     | Ledger posting successful            | `status_transition`       |
| DECIDED   | FAILED     | Ledger returned error or timeout     | `status_transition`       |

## Terminal States

| Status     | Meaning                                          | Money moved? |
|------------|--------------------------------------------------|--------------|
| `POSTED`   | Decision approved + ledger confirmed posting     | YES          |
| `REJECTED` | Decision hub explicitly rejected the transfer    | NO           |
| `FAILED`   | Infrastructure failure (hub or ledger down)      | NO           |

## Key Design Principles

### DECIDED ≠ POSTED

A transfer in `DECIDED` state means:
- The decision hub approved it
- **Money has NOT moved yet**
- The ledger call is pending

This distinction matters for retry logic. If the service restarts between
`DECIDED` and `POSTED`, a reconciliation job can query transfers in `DECIDED`
state and retry the ledger call.

### No implicit transitions

Every status change:
1. Updates `payment_transfers.status` + `updated_at`
2. Logs a structured `status_transition` event with `correlation_id`

There is no code path that changes status silently.

### REJECTED vs FAILED

- `REJECTED` = business decision (a rule said no)
- `FAILED` = infrastructure failure (something broke)

These are fundamentally different and must not be collapsed into one status.
A `REJECTED` transfer should never be retried automatically.
A `FAILED` transfer may be safe to retry (after investigation).

## Status in Legacy (AS-IS)

The legacy endpoint does not implement this state machine.
A transfer either posts or doesn't. No intermediate states.
If the ledger fails mid-flight, there is no queryable status.
