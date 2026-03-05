# MASONRY.AI Engine – multi-stage Docker image
# Build context: repo root
#
# docker build -f packages/engine/Dockerfile . -t masonry-engine

# ── Stage 1: builder ──────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential && \
    rm -rf /var/lib/apt/lists/*

COPY packages/engine /build/masonry-engine
RUN pip install --prefix=/install \
    fastapi uvicorn[standard] pydantic

# ── Stage 2: runtime ──────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

LABEL org.opencontainers.image.title="MASONRY.AI Engine"
LABEL org.opencontainers.image.description="Downstream analytics engine"
LABEL org.opencontainers.image.source="https://github.com/af0b9b/masonry-ai"
LABEL org.opencontainers.image.licenses="AGPL-3.0-or-later"

RUN useradd -m -u 1001 masonry
WORKDIR /app

COPY --from=builder /install /usr/local
COPY packages/engine/masonry_engine /app/masonry_engine

USER masonry

EXPOSE 8001

HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')"

CMD ["uvicorn", "masonry_engine.main:app", \
     "--host", "0.0.0.0", "--port", "8001", \
     "--workers", "2", "--log-level", "info"]
