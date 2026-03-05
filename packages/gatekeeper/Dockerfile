# MASONRY.AI Gatekeeper – multi-stage Docker image
# Build context: repo root (so we can COPY packages/core)
#
# docker build -f packages/gatekeeper/Dockerfile . -t masonry-gatekeeper

# ── Stage 1: builder ──────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# System deps for opendp compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && \
    rm -rf /var/lib/apt/lists/*

# Copy and install masonry-core first (dependency)
COPY packages/core /build/masonry-core
RUN pip install --prefix=/install /build/masonry-core

# Copy and install gatekeeper
COPY packages/gatekeeper /build/masonry-gatekeeper
RUN pip install --prefix=/install \
    fastapi uvicorn[standard] httpx pydantic \
    /build/masonry-gatekeeper || true

# ── Stage 2: runtime ──────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

LABEL org.opencontainers.image.title="MASONRY.AI Gatekeeper"
LABEL org.opencontainers.image.description="Privacy-by-default data proxy"
LABEL org.opencontainers.image.source="https://github.com/af0b9b/masonry-ai"
LABEL org.opencontainers.image.licenses="AGPL-3.0-or-later"

# Non-root user for security
RUN useradd -m -u 1001 masonry
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY packages/core/masonry_core /app/masonry_core
COPY packages/gatekeeper/masonry_gatekeeper /app/masonry_gatekeeper

USER masonry

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "masonry_gatekeeper.main:app", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "2", "--log-level", "info"]
