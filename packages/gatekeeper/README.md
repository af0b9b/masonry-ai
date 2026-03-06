# masonry-gatekeeper

**MASONRY.AI** — Layer 1 Gatekeeper: structural validation proxy with API key auth and rate limiting.

## Run

```bash
uvicorn masonry_gatekeeper.proxy:app --reload
```

Set `MASONRY_API_KEYS=your-key` and `ENGINE_URL=http://engine:8001` via environment variables.
