"""Canonical Gatekeeper proxy module.

Kept as a compatibility layer while `main.py` remains the executable entrypoint.
"""

from .main import app

__all__ = ["app"]

