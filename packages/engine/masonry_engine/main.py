"""masonry_engine.main – Core analytics engine for MASONRY.AI.

This service receives pre-sanitised data from the gatekeeper and
performs downstream processing: storage routing, lineage tracking,
and (in the commercial tier) ML-based anomaly detection.

Open stub: The ingest endpoint is open-source.
Commercial features (anomaly detection, graph DCDA) are in
`masonry_engine.commercial` (not included in this repo).
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="MASONRY.AI Engine",
    description="Downstream analytics engine (post-sanitisation).",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory store (replace with real DB in production)
# ---------------------------------------------------------------------------

_store: List[Dict[str, Any]] = []


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class IngestRequest(BaseModel):
    contract: str
    records: List[Dict[str, Any]]


class IngestResponse(BaseModel):
    batch_id: str
    contract: str
    records_stored: int
    timestamp: str


class LineageEntry(BaseModel):
    batch_id: str
    contract: str
    records_stored: int
    timestamp: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", tags=["ops"])
async def health() -> Dict[str, str]:
    return {"status": "ok", "service": "masonry-engine"}


@app.post(
    "/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["data"],
    summary="Ingest sanitised records from the gatekeeper.",
)
async def ingest(payload: IngestRequest) -> IngestResponse:
    """Store sanitised records and return a lineage batch ID."""
    if not payload.records:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No records provided.",
        )

    batch_id = str(uuid.uuid4())
    ts = datetime.now(timezone.utc).isoformat()

    for record in payload.records:
        _store.append({
            "batch_id": batch_id,
            "contract": payload.contract,
            "record": record,
            "ingested_at": ts,
        })

    return IngestResponse(
        batch_id=batch_id,
        contract=payload.contract,
        records_stored=len(payload.records),
        timestamp=ts,
    )


@app.get(
    "/lineage",
    response_model=List[LineageEntry],
    tags=["data"],
    summary="List ingestion lineage batches.",
)
async def lineage(
    contract: Optional[str] = None,
    limit: int = 50,
) -> List[LineageEntry]:
    """Return a summarised lineage log of ingested batches."""
    batches: Dict[str, LineageEntry] = {}
    for entry in _store:
        bid = entry["batch_id"]
        if bid not in batches:
            batches[bid] = LineageEntry(
                batch_id=bid,
                contract=entry["contract"],
                records_stored=0,
                timestamp=entry["ingested_at"],
            )
        batches[bid].records_stored += 1

    result = list(batches.values())
    if contract:
        result = [b for b in result if b.contract == contract]
    return result[-limit:]


@app.get(
    "/records",
    tags=["data"],
    summary="Retrieve stored sanitised records (dev only).",
)
async def get_records(
    batch_id: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Return raw stored records. Disable in production."""
    if os.getenv("MASONRY_ENV", "dev") != "dev":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Record dump disabled in non-dev environments.",
        )
    out = _store
    if batch_id:
        out = [r for r in out if r["batch_id"] == batch_id]
    return out[-limit:]


# ---------------------------------------------------------------------------
# Commercial feature placeholder
# ---------------------------------------------------------------------------

@app.post(
    "/analyse",
    tags=["commercial"],
    summary="[COMMERCIAL] Run anomaly detection pipeline.",
)
async def analyse(payload: IngestRequest) -> Dict[str, Any]:
    """Commercial anomaly detection - available in MASONRY.AI Pro tier."""
    raise HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail=(
            "Anomaly detection requires a MASONRY.AI Pro licence. "
            "Visit https://masonry.ai/pricing for details."
        ),
    )
