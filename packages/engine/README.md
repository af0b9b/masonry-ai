# masonry-engine

Privacy analytics engine for Masonry AI — MVPA differential privacy layer.

## Features

- Differential Privacy via Laplace/Gaussian mechanisms
- SQLAlchemy-backed result persistence
- Epsilon budget management per tenant
- REST API (FastAPI)

## Tiers

| Tier | Epsilon | Use Case |
|------|---------|----------|
| Shield (SMB) | 1.0 | Basic privacy |
| Trust (Mid-Market) | 0.5 | Balanced |
| Sovereign (Enterprise) | 0.1 | High privacy |

## Quick Start

```bash
pip install -e .
uvicorn masonry_engine.main:app --reload
```

## License

Proprietary — Masonry AI
