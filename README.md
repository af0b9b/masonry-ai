# MASONRY.AI

> **Zero Trust Data Architecture** — The open-core framework that makes GDPR, AI Act, and data privacy compliance *structurally impossible to bypass*.

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python](https://img.shields.io/badge/python-3.11+-green.svg)](https://www.python.org)
[![Framework](https://img.shields.io/badge/framework-FastAPI-009688.svg)](https://fastapi.tiangolo.com)

---

## The Problem

Most privacy tools are **reactive**: they discover violations *after* data has entered your systems. Audit dashboards, consent logs, and DPO workflows are necessary — but they don't prevent the breach.

**MASONRY changes the paradigm**: privacy is not a policy you enforce. It's a *physical constraint of the architecture*. If non-compliant data can't enter, it can't leak.

---

## Architecture: 3-Layer Zero Trust Data Flow

```
[ DATA SOURCE / USER INPUT ]
         |
         v
+----------------------------------------------------------+
| LAYER 1: INGRESS  (Privacy by Mason + Structural Privacy)|
| Gatekeeper — Schema validation + Privacy Predicates      |
| Fail-fast: non-compliant data is REJECTED at the gate    |
+----------------------------------------------------------+
         | (Only validated, "safe" data passes)
         v
+----------------------------------------------------------+
| LAYER 2: PROCESSING  (DCDA Light)                        |
| Decision Nodes — Stateless, isolated micro-functions     |
| Failures are contained. No cascading failures.           |
+----------------------------------------------------------+
         | (Raw analytical results)
         v
+----------------------------------------------------------+
| LAYER 3: OUTPUT  (Differential Privacy / NIST)           |
| Privacy Filter — OpenDP noise on aggregated outputs      |
| The data that leaves reveals nothing about individuals.  |
+----------------------------------------------------------+
         |
         v
[ DASHBOARD / API CONSUMER ]
```

---

## Core Concepts

### Privacy by Mason
Data is treated like raw material entering a construction site. The "Mason" (Layer 1) inspects every brick before it enters the structure. Non-conforming material is rejected immediately — **fail-fast, no exceptions**.

### DCDA Light (Decision-Centric Data Architecture)
Business logic is decomposed into **isolated, stateless Decision Nodes**. If one node fails, it doesn't cascade. Each node receives only the minimum data it needs (data minimization by design).

### Structural Privacy
Privacy is a property of the **container**, not the data. The architecture makes it physically impossible to process non-compliant data — not because developers remember to check, but because the pipeline rejects it.

---

## Quick Start

```bash
# Install core package (open source)
pip install masonry-core

# Or run the gatekeeper locally
git clone https://github.com/af0b9b/masonry-ai
cd masonry-ai/packages/gatekeeper
pip install -e .
uvicorn masonry_gatekeeper.proxy:app --reload
```

```python
from masonry_core.contracts import GDPRUserContract
from masonry_core.gatekeeper import mason_gate

# This data passes
safe = mason_gate(GDPRUserContract, {
    "user_id": "user-123",
    "age": 25,
    "email": "mario@example.com",
    "consent_level": 3,
    "gdpr_accepted": True
})
# safe.email == "m***@example.com"  <- masked at ingestion
# safe.user_id == "a3f9bc12..."     <- pseudonymized

# This data is REJECTED (age < 18)
mason_gate(GDPRUserContract, {"age": 15, ...})
# Raises: ValidationError - MASON STOP: age must be > 18
```

---

## Repository Structure

```text
masonry-ai/
├── README.md
├── pyproject.toml
└── packages/
    ├── core/                        <- @masonry/core [OPEN SOURCE]
    │   └── masonry_core/
    │       ├── contracts.py         <- Data Contract base
    │       ├── predicates.py        <- Privacy predicates
    │       ├── dp_filter.py         <- OpenDP wrapper (Layer 3)
    │       └── gatekeeper.py        <- Local Mason gate helper
    ├── gatekeeper/                  <- @masonry/gatekeeper [OPEN SOURCE]
    │   └── masonry_gatekeeper/
    │       ├── proxy.py             <- FastAPI proxy (Layer 1)
    │       ├── main.py              <- Service entrypoint
    │       └── templates/           <- GDPR/Health/Finance templates
    ├── engine/                      <- @masonry/engine [PROPRIETARY]
    │   └── masonry_engine/
    │       ├── graph.py             <- DCDA Decision Graph
    │       ├── nodes.py             <- Stateless Decision Nodes
    │       ├── stability.py         <- Turbulence score
    │       └── main.py              <- Service entrypoint
    ├── api/                         <- @masonry/api [PROPRIETARY]
    │   └── masonry_api/
    │       ├── main.py              <- FastAPI app
    │       ├── tenants.py           <- Multi-tenancy helpers
    │       └── audit.py             <- Immutable-style audit log
    └── dashboard/                   <- @masonry/dashboard [PROPRIETARY]
        └── src/
            ├── app/
            └── components/
                └── DecisionGraph.tsx
```

---

## Product Tiers

| Tier | Target | DCDA | Delivery | Price |
|------|--------|------|----------|-------|
| **Shield** | SMB / Startups | Hidden rules | Multi-tenant SaaS | €99/mo |
| **Trust** | Mid-Market (50-500) | 3-10 pre-configured nodes | Managed SaaS | €2k-5k/mo |
| **Sovereign** | Enterprise / PA | Full custom graph | Hybrid / VPC | Custom |

---

## Competitive Edge

| | OneTrust | Collibra | BigID | **MASONRY** |
|--|---------|---------|-------|-------------|
| Approach | Reactive audit | Data catalog | Discovery | **Preventive gate** |
| Privacy model | Policy-based | Policy-based | Scan-based | **Structural** |
| DCDA support | ❌ | ❌ | ❌ | **✅** |
| Code-native (CI/CD) | ❌ | ❌ | ❌ | **✅** |
| Mid-market ready | ❌ | ❌ | ⚠️ | **✅** |

---

## Tech Stack

- **Backend**: Python 3.11+ / FastAPI / Pydantic V2 / SQLAlchemy 2.0
- **Privacy**: OpenDP (SmartNoise) / Differential Privacy
- **Infra**: AWS (Lambda + RDS + API Gateway) / Pulumi IaC
- **Frontend**: Next.js + Tailwind + shadcn/ui + React Flow
- **Auth**: Auth0 / Clerk (multi-tenant OIDC)
- **Observability**: Sentry + Prometheus/Grafana

---

## Contributing

The `core` and `gatekeeper` packages are open source (AGPL-3.0). Contributions welcome.

The `engine` and `api` packages are proprietary (cloud service).

```bash
git clone https://github.com/af0b9b/masonry-ai
cd masonry-ai
pip install -e packages/core
pip install -e packages/gatekeeper
python -m pytest packages/core/tests/
```

---

## License

- `packages/core` + `packages/gatekeeper`: [GNU AGPL v3.0](LICENSE)
- `packages/engine` + `packages/api`: Proprietary — contact us

---

*Built with Structural Privacy. 🧱*
