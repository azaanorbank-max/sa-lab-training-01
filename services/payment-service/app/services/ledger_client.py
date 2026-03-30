"""
HTTP client for ledger-mock.

WHY explicit timeout:
  The ledger-mock supports X-Fail-Mode: TIMEOUT (sleeps 5s).
  Payment-service sets a 12s timeout to survive a real slow ledger,
  but the demo timeout mode will still complete within that window.

  In a real bank the ledger is the final authority on money movement.
  If it's unavailable, the transfer stays in DECIDED state — money
  has NOT moved. The status machine makes this explicit.
"""

import os
import uuid

import httpx
from pydantic import BaseModel

LEDGER_URL = os.getenv("LEDGER_URL", "http://localhost:8003")
TIMEOUT_SECONDS = 12.0


class PostingResult(BaseModel):
    posting_id: str
    status: str    # POSTED | FAILED
    fail_reason: str | None = None


async def post_transfer(
    *,
    transfer_id: str,
    amount: float,
    currency: str,
    correlation_id: str,
    fail_mode: str | None = None,
) -> PostingResult:
    """
    Submit a posting to ledger-mock.
    Raises httpx.HTTPError on network failure or non-2xx response.

    fail_mode is forwarded as X-Fail-Mode header (TIMEOUT | ERROR | DUPLICATE_TEST).
    """
    headers = {"X-Correlation-Id": correlation_id}
    if fail_mode:
        headers["X-Fail-Mode"] = fail_mode

    payload = {
        "transfer_id": transfer_id,
        "amount": amount,
        "currency": currency,
        "correlation_id": correlation_id,
    }

    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
        response = await client.post(
            f"{LEDGER_URL}/ledger/posting",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()

    return PostingResult(**response.json())
