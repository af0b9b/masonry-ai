"""MASONRY.AI — Gatekeeper Service (Layer 1: Structural/Mason)

Fix applied (Gemini code review):
  - API Key authentication via X-Masonry-Key header
  - SlowAPI rate limiting (60 req/min per IP)
  - Structured audit log for rejected data (no PII)
  - Async httpx forward to Engine with timeout + 502 handling
"""
from __future__ import annotations

import logging
import os
import time
import uuid
from typing import Any

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, Security, status
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel, ValidationError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from masonry_core.contracts import CONTRACT_REGISTRY, get_contract
from masonry_core.dp_filter import sanitise

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("masonry.gatekeeper")

# ---------------------------------------------------------------------------
# Rate limiter (SlowAPI)
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address)

# ---------------------------------------------------------------------------
# API Key Auth
# ---------------------------------------------------------------------------
API_KEY_NAME = "X-Masonry-Key"
_api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

VALID_API_KEYS: set[str] = set(
    filter(None, os.environ.get("MASONRY_API_KEYS", "dev-secret").split(","))
)


async def require_api_key(api_key: str = Security(_api_key_header)) -> str:
    """Validate API key. In production load from DB/Vault."""
    if api_key not in VALID_API_KEYS:
        log.warning("Rejected request — invalid API key")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing X-Masonry-Key",
        )
    return api_key


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="MASONRY.AI Gatekeeper",
    description="Layer 1 — Structural validation + Differential Privacy filter",
    version="0.2.0",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

ENGINE_URL = os.environ.get("ENGINE_URL", "http://engine:8001")


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class GatekeeperRequest(BaseModel):
    contract_type: str
    payload: dict[str, Any]


class GatekeeperResponse(BaseModel):
    status: str
    batch_id: str | None = None
    sanitised: dict[str, Any] | None = None
    rejection_reason: str | None = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _audit_rejection(request_id: str, contract_type: str, reason: str) -> None:
    """Structured rejection log — no raw PII emitted."""
    log.warning(
        "MASON_REJECT | request_id=%s contract=%s reason=%s ts=%f",
        request_id,
        contract_type,
        reason,
        time.time(),
    )


async def _forward_to_engine(
    sanitised_payload: dict[str, Any],
    contract_type: str,
    batch_id: str,
) -> dict[str, Any]:
    """Forward validated + DP-sanitised data to the Engine service."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{ENGINE_URL}/ingest",
            json={
                "contract_type": contract_type,
                "batch_id": batch_id,
                "data": sanitised_payload,
            },
        )
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.post("/sanitise", response_model=GatekeeperResponse)
@limiter.limit("60/minute")
async def sanitise_endpoint(
    request: Request,
    body: GatekeeperRequest,
    _key: str = Depends(require_api_key),
) -> GatekeeperResponse:
    """Validate payload against Data Contract, apply DP filter, forward to Engine."""
    request_id = str(uuid.uuid4())

    # 1. Resolve contract class
    ContractClass = get_contract(body.contract_type)
    if ContractClass is None:
        _audit_rejection(request_id, body.contract_type, "unknown_contract")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown contract type: {body.contract_type}",
        )

    # 2. Structural validation (Mason Fail-Fast)
    try:
        validated = ContractClass(**body.payload)
    except (ValidationError, ValueError) as exc:
        reason = str(exc)
        _audit_rejection(request_id, body.contract_type, reason)
        return GatekeeperResponse(status="rejected", rejection_reason=reason)

    # 3. Differential Privacy sanitisation
    safe_data = sanitise(validated.model_dump())

    # 4. Forward to Engine
    batch_id = str(uuid.uuid4())
    try:
        await _forward_to_engine(safe_data, body.contract_type, batch_id)
    except httpx.HTTPError as exc:
        log.error("Engine unreachable: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Downstream engine unavailable",
        ) from exc

    log.info("MASON_ACCEPT | request_id=%s batch_id=%s", request_id, batch_id)
    return GatekeeperResponse(
        status="accepted",
        batch_id=batch_id,
        sanitised=safe_data,
    )


@app.get("/contracts")
async def list_contracts(_key: str = Depends(require_api_key)) -> dict:
    """Introspection: list available Data Contracts."""
    return {"contracts": list(CONTRACT_REGISTRY.keys())}


@app.get("/health")
async def health() -> dict:
    """Health check — no auth required."""
    return {"status": "ok", "service": "gatekeeper", "version": "0.2.0"}
