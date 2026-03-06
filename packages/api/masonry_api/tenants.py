"""Multi-tenancy helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TenantContext:
    tenant_id: str
    plan: str = "shield"


def resolve_tenant(tenant_id: str | None) -> TenantContext:
    if not tenant_id:
        return TenantContext(tenant_id="public")
    return TenantContext(tenant_id=tenant_id)
