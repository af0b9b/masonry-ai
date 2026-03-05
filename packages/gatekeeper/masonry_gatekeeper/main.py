"""masonry_gatekeeper.main – FastAPI proxy that enforces Mason contracts.

This is the OPEN-SOURCE gatekeeper layer. It:
  1. Validates incoming data against a named MasonContract.
  2. Applies the DP sanitisation pipeline (masonry_core.dp_filter).
  3. Forwards the clean payload to the downstream engine.

Start with:
    uvicorn masonry_gatekeeper.main:app --reload
"""
from __future__ import annotations

import os
import httpx
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from masonry_core import get_contract, sanitise
from masonry_core.contracts import MasonContract

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="MASONRY.AI Gatekeeper",
    description="Privacy-by-default data proxy – open-source layer.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

ENGINE_URL = os.getenv("MASONRY_ENGINE_URL", "http://localhost:8001")


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class GatekeeperRequest(BaseModel):
    contract: str = Field(
        ...,
        description="Name of the MasonContract to enforce (e.g. 'gdpr_basic').",
        example="gdpr_basic",
    )
    records: List[Dict[str, Any]] = Field(
        ...,
        description="List of data records to validate and sanitise.",
    )
    epsilon_override: Optional[float] = Field(
        None,
        description="Override privacy budget epsilon (advanced users).",
        ge=0.001,
        le=10.0,
    )
    forward_to_engine: bool = Field(
        True,
        description="If True, forward sanitised payload to the engine service.",
    )


class GatekeeperResponse(BaseModel):
    contract_used: str
    records_in: int
    records_out: int
    sanitised_records: List[Dict[str, Any]]
    engine_response: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health", tags=["ops"])
async def health() -> Dict[str, str]:
    return {"status": "ok", "service": "masonry-gatekeeper"}


# ---------------------------------------------------------------------------
# Core endpoint
# ---------------------------------------------------------------------------

@app.post(
    "/sanitise",
    response_model=GatekeeperResponse,
    status_code=status.HTTP_200_OK,
    tags=["privacy"],
    summary="Validate, sanitise, and optionally forward data.",
)
async def sanitise_endpoint(payload: GatekeeperRequest) -> GatekeeperResponse:
    # 1. Resolve contract
    try:
        contract_cls: type[MasonContract] = get_contract(payload.contract)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    # 2. Validate each record against the contract schema
    validated: List[Dict[str, Any]] = []
    errors: List[str] = []
    for idx, record in enumerate(payload.records):
        try:
            obj = contract_cls(**record)
            validated.append(obj.model_dump())
        except Exception as exc:  # pydantic ValidationError
            errors.append(f"record[{idx}]: {exc}")

    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"validation_errors": errors},
        )

    # 3. DP sanitisation
    contract_instance = contract_cls(**validated[0]) if validated else contract_cls()
    clean = sanitise(
        validated,
        contract_instance,
        epsilon_override=payload.epsilon_override,
    )

    # 4. (Optional) forward to engine
    engine_resp: Optional[Dict[str, Any]] = None
    if payload.forward_to_engine:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{ENGINE_URL}/ingest",
                    json={"contract": payload.contract, "records": clean},
                )
                resp.raise_for_status()
                engine_resp = resp.json()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Engine returned {exc.response.status_code}: {exc.response.text}",
            )
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Engine unreachable: {exc}",
            )

    return GatekeeperResponse(
        contract_used=payload.contract,
        records_in=len(payload.records),
        records_out=len(clean),
        sanitised_records=clean,
        engine_response=engine_resp,
    )


# ---------------------------------------------------------------------------
# Contract introspection
# ---------------------------------------------------------------------------

@app.get("/contracts", tags=["meta"])
async def list_contracts() -> Dict[str, Any]:
    """List all available contracts and their required fields."""
    from masonry_core.contracts import CONTRACT_REGISTRY
    result = {}
    for name, cls in CONTRACT_REGISTRY.items():
        schema = cls.model_json_schema()
        result[name] = {
            "title": schema.get("title"),
            "required": schema.get("required", []),
            "properties": list(schema.get("properties", {}).keys()),
        }
    return result
