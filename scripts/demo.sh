#!/usr/bin/env bash
# ============================================================
# Decision Hub — Demo Script
# 4 scenarios that illustrate the architecture principles
# ============================================================
# Usage:
#   ./scripts/demo.sh          # run all scenarios
#   ./scripts/demo.sh A        # run scenario A only
#   ./scripts/demo.sh B        # run scenario B only
#   ./scripts/demo.sh C        # run scenario C only
#   ./scripts/demo.sh D        # run scenario D only
# ============================================================

set -euo pipefail

GW="http://localhost:8000"
HUB="http://localhost:8002"
BOLD="\033[1m"
CYAN="\033[36m"
GREEN="\033[32m"
YELLOW="\033[33m"
RED="\033[31m"
RESET="\033[0m"

header() {
  echo ""
  echo -e "${CYAN}${BOLD}══════════════════════════════════════════════════${RESET}"
  echo -e "${CYAN}${BOLD}  $1${RESET}"
  echo -e "${CYAN}${BOLD}══════════════════════════════════════════════════${RESET}"
}

step() {
  echo ""
  echo -e "${YELLOW}▶ $1${RESET}"
}

note() {
  echo -e "${GREEN}  ✓ $1${RESET}"
}

pretty() {
  # Pretty-print JSON if jq is available
  if command -v jq &>/dev/null; then
    echo "$1" | jq .
  else
    echo "$1"
  fi
}

wait_for_services() {
  echo "Waiting for services to be ready..."
  for svc in "$GW/health" "$HUB/health"; do
    for i in $(seq 1 30); do
      if curl -sf "$svc" > /dev/null 2>&1; then
        echo "  ✓ $svc"
        break
      fi
      sleep 2
    done
  done
}

# ============================================================
# SCENARIO A — Explainability
# Goal: show structured reasons + audit trail vs legacy chaos
# ============================================================
scenario_a() {
  header "SCENARIO A — Explainability (why was it rejected?)"

  echo ""
  echo "  Business question: 'Why was this transfer rejected?'"
  echo "  AS-IS answer: a string. TO-BE answer: structured, traceable."

  CORR_ID="demo-corr-$(date +%s)"

  # ── A1: TO-BE — structured rejection ──
  step "A1. TO-BE: POST /api/p2p/transfer with country=IR (AML trigger)"
  RESPONSE=$(curl -s -X POST "$GW/api/p2p/transfer" \
    -H "Content-Type: application/json" \
    -H "Idempotency-Key: demo-a-tobe-$(date +%s)" \
    -H "X-Correlation-Id: $CORR_ID" \
    -d '{
      "client_id": "client-001",
      "receiver_id": "receiver-ir-001",
      "amount": 50000,
      "currency": "KZT",
      "country": "IR",
      "device_trust": "HIGH",
      "daily_sum": 0
    }')

  pretty "$RESPONSE"

  DECISION_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('decision',{}).get('decision_id',''))" 2>/dev/null || echo "")

  note "status=REJECTED"
  note "decision.reasons[0].rule_id = AML_102"
  note "decision.reasons[0].owner = compliance"
  note "decision.reasons[0].reason_code = AML_COUNTRY_BLOCKED"

  if [ -n "$DECISION_ID" ]; then
    echo ""
    step "A2. Fetch full audit record: GET /decision/audit/$DECISION_ID"
    AUDIT=$(curl -s "$HUB/decision/audit/$DECISION_ID")
    pretty "$AUDIT"
    note "audit shows: ALL rules evaluated (not just the one that fired)"
    note "transfer_context snapshot preserved — reproducible at any time"
  fi

  # ── A3: Legacy — no audit, no structure ──
  echo ""
  step "A3. LEGACY: POST /api/p2p/transfer-legacy with same input"
  LEGACY=$(curl -s -X POST "$GW/api/p2p/transfer-legacy" \
    -H "Content-Type: application/json" \
    -H "Idempotency-Key: demo-a-legacy-$(date +%s)" \
    -d '{
      "client_id": "client-001",
      "receiver_id": "receiver-ir-001",
      "amount": 50000,
      "currency": "KZT",
      "country": "IR",
      "device_trust": "HIGH",
      "daily_sum": 0
    }')

  pretty "$LEGACY"

  echo ""
  echo -e "${RED}  ✗ Legacy has: reason='AML_BLOCKED' (a string)${RESET}"
  echo -e "${RED}  ✗ Legacy has: no rule_id, no owner, no version, no audit_id${RESET}"
  echo -e "${RED}  ✗ Auditor asks 'show me the log' → it doesn't exist${RESET}"
  echo ""
  note "CONCLUSION: TO-BE answers every compliance question. Legacy answers none."
}

# ============================================================
# SCENARIO B — Change rule without release
# Goal: show rules are data, not code
# ============================================================
scenario_b() {
  header "SCENARIO B — Change rule without release"

  echo ""
  echo "  Business: 'Lower the daily limit from 10M to 100K immediately.'"
  echo "  AS-IS: Write ticket → Dev codes it → QA → CAB → Deploy (days)"
  echo "  TO-BE: PATCH /decision/rules/LIMIT_DAILY (seconds)"

  AMOUNT=500000
  DAILY_SUM=0

  step "B1. Current rules (before change)"
  curl -s "$HUB/decision/rules" | python3 -c "
import sys, json
rules = json.load(sys.stdin)
for r in rules:
    print(f\"  {r['rule_id']:15} priority={r['priority']} active={r['active']} threshold={r.get('condition_params',{}).get('threshold','n/a')}\")"

  step "B2. POST transfer: amount=$AMOUNT, daily_sum=$DAILY_SUM (should APPROVE — sum=$((AMOUNT+DAILY_SUM)) < 10M)"
  R1=$(curl -s -X POST "$GW/api/p2p/transfer" \
    -H "Content-Type: application/json" \
    -H "Idempotency-Key: demo-b-before-$(date +%s)" \
    -d "{
      \"client_id\": \"client-002\",
      \"receiver_id\": \"receiver-002\",
      \"amount\": $AMOUNT,
      \"currency\": \"KZT\",
      \"country\": \"KZ\",
      \"device_trust\": \"HIGH\",
      \"daily_sum\": $DAILY_SUM
    }")
  echo "  Status: $(echo "$R1" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','?'))" 2>/dev/null)"
  note "APPROVED — 500K + 0 = 500K < 10,000,000 limit"

  step "B3. PATCH LIMIT_DAILY: lower threshold to 100,000"
  PATCH_RESULT=$(curl -s -X PATCH "$HUB/decision/rules/LIMIT_DAILY" \
    -H "Content-Type: application/json" \
    -d '{
      "condition_params": {
        "fields": ["daily_sum", "amount"],
        "operator": "SUM_GT",
        "threshold": 100000
      }
    }')
  pretty "$PATCH_RESULT"
  note "Rule updated in-place. No code changed. No service restarted."

  sleep 1

  step "B4. Same transfer again — now should REJECT (500K > new 100K limit)"
  R2=$(curl -s -X POST "$GW/api/p2p/transfer" \
    -H "Content-Type: application/json" \
    -H "Idempotency-Key: demo-b-after-$(date +%s)" \
    -d "{
      \"client_id\": \"client-002\",
      \"receiver_id\": \"receiver-002\",
      \"amount\": $AMOUNT,
      \"currency\": \"KZT\",
      \"country\": \"KZ\",
      \"device_trust\": \"HIGH\",
      \"daily_sum\": $DAILY_SUM
    }")
  pretty "$R2"
  note "Now REJECTED — 500K > 100K (new threshold)"

  step "B5. Restore original threshold (10,000,000)"
  curl -s -X PATCH "$HUB/decision/rules/LIMIT_DAILY" \
    -H "Content-Type: application/json" \
    -d '{
      "condition_params": {
        "fields": ["daily_sum", "amount"],
        "operator": "SUM_GT",
        "threshold": 10000000
      }
    }' | python3 -c "import sys,json; r=json.load(sys.stdin); print(f\"  Restored threshold: {r['condition_params']['threshold']}\")" 2>/dev/null

  note "CONCLUSION: payment-service code did NOT change. Zero deployments."
}

# ============================================================
# SCENARIO C — Idempotency
# Goal: two identical requests → one transfer, one posting
# ============================================================
scenario_c() {
  header "SCENARIO C — Idempotency"

  echo ""
  echo "  Business problem: mobile app retries on network timeout."
  echo "  Without idempotency: duplicate debit. Customer angry."
  echo "  With idempotency: same key = same result, no duplicate."

  IDEM_KEY="demo-idem-key-$(date +%s)"

  PAYLOAD='{
    "client_id": "client-003",
    "receiver_id": "receiver-003",
    "amount": 10000,
    "currency": "KZT",
    "country": "KZ",
    "device_trust": "HIGH",
    "daily_sum": 0
  }'

  step "C1. First request (Idempotency-Key: $IDEM_KEY)"
  R1=$(curl -s -X POST "$GW/api/p2p/transfer" \
    -H "Content-Type: application/json" \
    -H "Idempotency-Key: $IDEM_KEY" \
    -d "$PAYLOAD")
  pretty "$R1"
  T1=$(echo "$R1" | python3 -c "import sys,json; print(json.load(sys.stdin).get('transfer_id','?'))" 2>/dev/null)
  note "transfer_id = $T1"
  note "idempotent = false (first call)"

  sleep 1

  step "C2. Retry — SAME Idempotency-Key: $IDEM_KEY"
  R2=$(curl -s -X POST "$GW/api/p2p/transfer" \
    -H "Content-Type: application/json" \
    -H "Idempotency-Key: $IDEM_KEY" \
    -d "$PAYLOAD")
  pretty "$R2"
  T2=$(echo "$R2" | python3 -c "import sys,json; print(json.load(sys.stdin).get('transfer_id','?'))" 2>/dev/null)
  note "transfer_id = $T2"
  note "idempotent = true (replay from cache)"

  if [ "$T1" = "$T2" ]; then
    note "transfer_ids are IDENTICAL — no duplicate created"
  else
    echo -e "${RED}  ✗ ERROR: transfer_ids differ — idempotency broken!${RESET}"
  fi

  note "CONCLUSION: Ledger posting count for this transfer_id = 1 (always)"
}

# ============================================================
# SCENARIO D — Partial failure / retry
# Goal: show explicit status lifecycle and failure handling
# ============================================================
scenario_d() {
  header "SCENARIO D — Partial failure (DECIDED ≠ POSTED)"

  echo ""
  echo "  Lesson: A decision approval does NOT guarantee money moved."
  echo "  Status machine makes failure states explicit and queryable."

  step "D1. POST transfer with X-Fail-Mode: ERROR (ledger will fail)"
  R1=$(curl -s -X POST "$GW/api/p2p/transfer" \
    -H "Content-Type: application/json" \
    -H "Idempotency-Key: demo-d-fail-$(date +%s)" \
    -H "X-Fail-Mode: ERROR" \
    -d '{
      "client_id": "client-004",
      "receiver_id": "receiver-004",
      "amount": 25000,
      "currency": "KZT",
      "country": "KZ",
      "device_trust": "HIGH",
      "daily_sum": 0
    }')
  pretty "$R1"

  STATUS=$(echo "$R1" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','?'))" 2>/dev/null)
  DEC=$(echo "$R1" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('decision',{}).get('decision','?'))" 2>/dev/null)

  note "status = $STATUS (transfer failed at ledger step)"
  note "decision.decision = $DEC (hub approved — this is key)"
  echo ""
  echo -e "${YELLOW}  Decision was APPROVED. Ledger FAILED. These are separate facts.${RESET}"
  echo -e "${YELLOW}  status=FAILED means: money did NOT move.${RESET}"
  echo -e "${YELLOW}  A reconciliation job can query status=DECIDED to find stuck transfers.${RESET}"

  sleep 1

  step "D2. Retry with new Idempotency-Key, no X-Fail-Mode (should succeed)"
  R2=$(curl -s -X POST "$GW/api/p2p/transfer" \
    -H "Content-Type: application/json" \
    -H "Idempotency-Key: demo-d-retry-$(date +%s)" \
    -d '{
      "client_id": "client-004",
      "receiver_id": "receiver-004",
      "amount": 25000,
      "currency": "KZT",
      "country": "KZ",
      "device_trust": "HIGH",
      "daily_sum": 0
    }')
  pretty "$R2"
  note "status = $(echo "$R2" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','?'))" 2>/dev/null)"
  note "CONCLUSION: Status machine is explicit. DECIDED ≠ POSTED. Failures are queryable."
}

# ── Main ──────────────────────────────────────────────────────────────────────

wait_for_services

SCENARIO="${1:-ALL}"

case "$SCENARIO" in
  A) scenario_a ;;
  B) scenario_b ;;
  C) scenario_c ;;
  D) scenario_d ;;
  ALL)
    scenario_a
    echo ""
    read -rp "Press ENTER to continue to Scenario B..." || true
    scenario_b
    echo ""
    read -rp "Press ENTER to continue to Scenario C..." || true
    scenario_c
    echo ""
    read -rp "Press ENTER to continue to Scenario D..." || true
    scenario_d
    ;;
  *)
    echo "Usage: $0 [A|B|C|D|ALL]"
    exit 1
    ;;
esac

echo ""
echo -e "${GREEN}${BOLD}══════════════════════════════════════════════════${RESET}"
echo -e "${GREEN}${BOLD}  Demo complete.${RESET}"
echo -e "${GREEN}${BOLD}══════════════════════════════════════════════════${RESET}"
echo ""
