"""Immutable-style audit records (in-memory bootstrap)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class AuditEvent:
    event_id: str
    tenant_id: str
    action: str
    at: datetime
    payload: dict[str, Any]


_AUDIT_EVENTS: list[AuditEvent] = []


def append_event(event: AuditEvent) -> None:
    _AUDIT_EVENTS.append(event)


def list_events(tenant_id: str) -> list[AuditEvent]:
    return [evt for evt in _AUDIT_EVENTS if evt.tenant_id == tenant_id]


def now_utc() -> datetime:
    return datetime.now(UTC)
