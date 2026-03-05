# masonry-core

**MASONRY.AI** — Open-core Python library implementing the Mason validation layer (Layer 1) and Differential Privacy filter (Layer 3).

## Packages

- `masonry_core.contracts` — Pydantic v2 Data Contracts (GDPR, Finance, Health)
- `masonry_core.dp_filter` — OpenDP-backed DP sanitisation pipeline

## Install

```bash
pip install masonry-core
```

## Usage

```python
from masonry_core.contracts import GDPRUserContract
from masonry_core.dp_filter import sanitise

validated = GDPRUserContract(user_id=1, age=25, email="user@example.com", consent_level=2, gdpr_accepted=True)
safe = sanitise(validated.model_dump())
```

See the [main repo README](../../README.md) for full architecture documentation.
