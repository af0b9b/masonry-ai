"""masonry_engine.main — Core analytics engine for MASONRY.AI.

Fix applied (Gemini code review):
  - Replace in-memory list with SQLAlchemy + SQLite (dev) / PostgreSQL (prod)
  - Thread-safe writes via SQLAlchemy session factory
  - Startup / shutdown lifecycle for DB connection pool
  - /records endpoint gated behind DEBUG env flag

In production set DATABASE_URL=postgresql+asyncpg://user:pass@host/db
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import Column, DateTime, String, Text, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# ---------------------------------------------------------------------------
# Database setup
# ---------------------------------------------------------------------------
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./masonry_engine.db")

# Use check_same_thread=False only for SQLite (safe with session-per-request)
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine_db = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine_db, autocommit=False, autoflush=False)

DEBUG = os.environ.get("MASONRY_DEBUG", "false").lower() == "true"


class Base(DeclarativeBase):
    pass


class Record(Base):
    __tablename__ = "records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    batch_id = Column(String(36), nullable=False, index=True)
    contract_type = Column(String(64), nullable=False)
    data = Column(Text, nullable=False)  # JSON-serialised sanitised payload
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="MASONRY.AI Engine",
    description="Downstream analytics engine (post-sanitisation).",
    version="0.2.0",
)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine_db)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class IngestRequest(BaseModel):
    contract_type: str
    batch_id: str
    data: dict[str, Any]


class IngestResponse(BaseModel):
    status: str
    record_id: str
    batch_id: str


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------
import json  # noqa: E402


def _get_db() -> Session:
    return SessionLocal()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.post("/ingest", response_model=IngestResponse)
def ingest(body: IngestRequest) -> IngestResponse:
    """Persist a sanitised record from the Gatekeeper."""
    record_id = str(uuid.uuid4())
    record = Record(
        id=record_id,
        batch_id=body.batch_id,
        contract_type=body.contract_type,
        data=json.dumps(body.data),
    )
    db = _get_db()
    try:
        db.add(record)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DB write failed: {exc}",
        ) from exc
    finally:
        db.close()

    return IngestResponse(status="stored", record_id=record_id, batch_id=body.batch_id)


@app.get("/lineage")
def lineage(batch_id: str) -> dict:
    """Summarise all records for a given batch_id."""
    db = _get_db()
    try:
        rows = db.query(Record).filter(Record.batch_id == batch_id).all()
    finally:
        db.close()

    return {
        "batch_id": batch_id,
        "record_count": len(rows),
        "contract_types": list({r.contract_type for r in rows}),
        "oldest": min((r.created_at for r in rows), default=None),
        "newest": max((r.created_at for r in rows), default=None),
    }


@app.get("/records")
def dump_records() -> list[dict]:
    """Dev-only: dump all records. Disabled in production."""
    if not DEBUG:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="/records endpoint is disabled in production. Set MASONRY_DEBUG=true.",
        )
    db = _get_db()
    try:
        rows = db.query(Record).order_by(Record.created_at.desc()).limit(100).all()
    finally:
        db.close()
    return [
        {
            "id": r.id,
            "batch_id": r.batch_id,
            "contract_type": r.contract_type,
            "data": json.loads(r.data),
            "created_at": r.created_at,
        }
        for r in rows
    ]


@app.post("/analyse")
def analyse() -> dict:
    """Commercial feature stub (DCDA graph analytics)."""
    raise HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail="Graph analytics requires MASONRY.AI Trust or Sovereign tier.",
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "engine", "version": "0.2.0"}
