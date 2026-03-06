"""Reusable privacy predicates for Mason contracts."""

from __future__ import annotations

import hashlib


class PrivacyPredicate:
    """Utility predicates applied at ingestion boundaries."""

    @staticmethod
    def mask_email(value: str) -> str:
        parts = value.split("@")
        if len(parts) != 2:
            raise ValueError("Invalid email format")
        local = parts[0]
        masked = (local[0] + "***") if len(local) > 1 else "***"
        return f"{masked}@{parts[1]}"

    @staticmethod
    def pseudonymize(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def mask_partial(value: str, keep: int = 2) -> str:
        if len(value) <= keep:
            return "*" * len(value)
        return value[:keep] + "*" * (len(value) - keep)

