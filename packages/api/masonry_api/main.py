"""Main Masonry API service."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

from .audit import AuditEvent, append_event, list_events, now_utc
from .tenants import resolve_tenant

app = FastAPI(title="MASONRY.AI API", version="0.1.0")


class AuditIn(BaseModel):
    tenant_id: str | None = None
    action: str
    payload: dict[str, Any] = {}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "api", "version": "0.1.0"}


@app.post("/audit")
def create_audit(event: AuditIn) -> dict[str, str]:
    tenant = resolve_tenant(event.tenant_id)
    record = AuditEvent(
        event_id=str(uuid.uuid4()),
        tenant_id=tenant.tenant_id,
        action=event.action,
        at=now_utc(),
        payload=event.payload,
    )
    append_event(record)
    return {"status": "stored", "event_id": record.event_id}


@app.get("/audit/{tenant_id}")
def get_audit(tenant_id: str) -> dict[str, Any]:
    events = list_events(tenant_id)
    return {
        "tenant_id": tenant_id,
        "count": len(events),
        "events": [
            {
                "event_id": e.event_id,
                "action": e.action,
                "at": e.at.isoformat(),
            }
            for e in events
        ],
    }
