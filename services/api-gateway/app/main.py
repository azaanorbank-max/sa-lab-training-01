"""
api-gateway — security boundary, context propagation, routing.

RESPONSIBILITIES (exactly these, no more):
  1. Generate X-Correlation-Id if client did not provide one
  2. Forward Idempotency-Key and X-Fail-Mode headers downstream
  3. Route /api/p2p/* → payment-service
  4. Rate-limit signaling (X-RateLimit-* headers in response)
  5. Return uniform error format if downstream is unreachable

DOES NOT:
  - Implement any business logic
  - Make decisions about transfers
  - Store any state
  - Authenticate (out of scope for this demo — add JWT validation here)

WHY a gateway matters:
  Without a gateway, clients call internal services directly. This means:
  - No central point for correlation-id injection
  - No single place to add auth, rate limiting, or TLS termination
  - Internal service URLs leak to clients
  - Every service re-implements the same cross-cutting concerns

PORT: 8000
"""

import os
import uuid

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from shared.correlation import CorrelationMiddleware, get_correlation_id, set_correlation_id
from shared.logging import get_logger

SERVICE_NAME = os.getenv("SERVICE_NAME", "api-gateway")
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "http://localhost:8001")

logger = get_logger(SERVICE_NAME)

app = FastAPI(title="API Gateway", version="1.0.0")
app.add_middleware(CorrelationMiddleware, generate_if_missing=True)

# Headers to forward from client to downstream
_FORWARD_HEADERS = {"idempotency-key", "x-correlation-id", "x-fail-mode", "content-type"}


def _build_forward_headers(request: Request, correlation_id: str) -> dict:
    headers = {"X-Correlation-Id": correlation_id}
    for key, value in request.headers.items():
        if key.lower() in _FORWARD_HEADERS and key.lower() != "x-correlation-id":
            headers[key] = value
    return headers


async def _proxy(request: Request, upstream_path: str):
    correlation_id = get_correlation_id()
    forward_headers = _build_forward_headers(request, correlation_id)

    body = await request.body()

    logger.info(
        "proxying request",
        extra={
            "service": SERVICE_NAME,
            "correlation_id": correlation_id,
            "event": "proxy_request",
            "path": request.url.path,
            "upstream": f"{PAYMENT_SERVICE_URL}{upstream_path}",
        },
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            upstream_response = await client.request(
                method=request.method,
                url=f"{PAYMENT_SERVICE_URL}{upstream_path}",
                content=body,
                headers=forward_headers,
            )
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        logger.error(
            "upstream unreachable",
            extra={
                "service": SERVICE_NAME,
                "correlation_id": correlation_id,
                "event": "upstream_unreachable",
                "upstream": PAYMENT_SERVICE_URL,
                "error": str(exc),
            },
        )
        return JSONResponse(
            status_code=503,
            content={
                "error_code": "UPSTREAM_UNAVAILABLE",
                "message": "Payment service is unavailable",
                "correlation_id": correlation_id,
                "service": SERVICE_NAME,
            },
            headers={"X-Correlation-Id": correlation_id},
        )

    # Forward the upstream response with correlation-id header added
    response_headers = {
        "X-Correlation-Id": correlation_id,
        "X-RateLimit-Limit": "100",
        "X-RateLimit-Remaining": "99",
    }
    if "content-type" in upstream_response.headers:
        response_headers["content-type"] = upstream_response.headers["content-type"]

    logger.info(
        "proxy response",
        extra={
            "service": SERVICE_NAME,
            "correlation_id": correlation_id,
            "event": "proxy_response",
            "status_code": upstream_response.status_code,
            "upstream_path": upstream_path,
        },
    )

    return JSONResponse(
        status_code=upstream_response.status_code,
        content=upstream_response.json(),
        headers=response_headers,
    )


@app.post("/api/p2p/transfer")
async def transfer(request: Request):
    return await _proxy(request, "/p2p/transfer")


@app.post("/api/p2p/transfer-legacy")
async def transfer_legacy(request: Request):
    return await _proxy(request, "/p2p/transfer-legacy")


@app.get("/health")
async def health():
    return {"status": "ok", "service": SERVICE_NAME}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    correlation_id = get_correlation_id()
    logger.error(
        "unhandled gateway exception",
        extra={
            "service": SERVICE_NAME,
            "correlation_id": correlation_id,
            "event": "unhandled_exception",
            "error": str(exc),
        },
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error_code": "GATEWAY_ERROR",
            "message": "Gateway error",
            "correlation_id": correlation_id,
            "service": SERVICE_NAME,
        },
    )
