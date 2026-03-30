"""
HTTP client for decision-hub.

WHY a dedicated client module:
  1. Payment-service must not know HOW decision-hub evaluates rules.
     It only sends context and receives a decision. Clean boundary.
  2. All HTTP config (URL, timeout) is in one place.
  3. Timeout handling is explicit — if decision-hub is slow or down,
     the transfer goes to FAILED, not stuck forever.

TIMEOUT: 10s. In a real bank this would be configurable per decision_type.
"""

import os

import httpx
from pydantic import BaseModel

DECISION_HUB_URL = os.getenv("DECISION_HUB_URL", "http://localhost:8002")
TIMEOUT_SECONDS = 10.0


class DecisionReason(BaseModel):
    rule_id: str
    reason_code: str
    owner: str


class DecisionResult(BaseModel):
    decision_id: str
    allowed: bool
    decision: str
    reasons: list[DecisionReason]
    risk_score: float | None
    rules_evaluated: int
    rules_matched: int


async def evaluate(
    *,
    client_id: str,
    receiver_id: str,
    amount: float,
    currency: str,
    country: str,
    device_trust: str,
    daily_sum: float,
    correlation_id: str,
) -> DecisionResult:
    """
    Call decision-hub to evaluate a P2P transfer.
    Raises httpx.HTTPError on network failure or non-2xx response.
    """
    payload = {
        "decision_type": "P2P_TRANSFER",
        "context": {
            "client_id": client_id,
            "receiver_id": receiver_id,
            "amount": amount,
            "currency": currency,
            "country": country,
            "device_trust": device_trust,
            "daily_sum": daily_sum,
        },
        "correlation_id": correlation_id,
    }

    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
        response = await client.post(
            f"{DECISION_HUB_URL}/decision/evaluate",
            json=payload,
            headers={"X-Correlation-Id": correlation_id},
        )
        response.raise_for_status()

    return DecisionResult(**response.json())
