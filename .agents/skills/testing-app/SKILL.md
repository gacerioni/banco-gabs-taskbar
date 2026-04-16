# Testing Redis Global Search Taskbar

## Prerequisites

- Redis 8.6+ instance with FT.HYBRID support
- REDIS_URL environment variable set (or in `.env` file)
- Python 3.11+ (for local) or Docker (for containerized)

## Starting the App

### Local
```bash
source .env && ./run.sh
```
Or:
```bash
source .env && uvicorn main:app --reload
```

### Docker
```bash
REDIS_URL=redis://... docker compose up
```
Docker compose auto-reads `.env` from the project directory for variable substitution.

## Startup Behavior

- App pre-warms ML models at startup (~10-15s): vectorizer, language detector, 3 semantic routers (pt/en/es)
- Auto-seeds Redis indexes if they don't exist (creates routes, products, SKUs)
- Logs show "Server ready! First search will be fast." when startup is complete

## Key Endpoints

| Endpoint | Description |
|---|---|
| `GET /` | Main search UI |
| `GET /admin` | Admin dashboard |
| `GET /api/search?q=pix&limit=5` | Hybrid search API |
| `GET /autocomplete?q=pi&limit=5` | Autocomplete suggestions |
| `GET /health` | Health check |
| `GET /api/feedback/stats` | Feedback statistics |

## Testing Search

### Portuguese (primary demo language)
- `pix` → should return Pix route as #1, intent=SEARCH, confidence=100%
- `como funciona o pix` → should route to CHAT intent
- `bloquear cartao` → should return Bloquear Cartao route, intent=SEARCH

### English
- `send money` → intent=SEARCH, 100% confidence
- Note: English chat routing is weak (only 41 chat examples vs 153 search)

## Verifying Search Response

A healthy search response includes:
- `breakdown.embedding_ms` — time to generate embedding
- `breakdown.redis_search_ms` — time for Redis FT.HYBRID
- `breakdown.cache_hit` — whether result was cached
- `language` — detected language (pt/en/es)
- `intent` — SEARCH or CHAT
- `confidence` — routing confidence percentage
- `results[]` with `match_explanation` on each item

## Docker Testing

1. Build and start: `REDIS_URL=... docker compose up -d`
2. Check logs: `docker compose logs --tail=30`
3. Verify "Server ready!" in logs
4. Test search: `curl "http://localhost:8000/api/search?q=pix&limit=2"`
5. Verify `.env` is NOT in the image: `docker compose exec app ls /app/.env` should fail

## Default Embedding Model

- MiniLM (`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, 384 dims)
- Fast cold-start (~2s), good for demos
- For Qwen (production quality), set `EMBEDDING_MODEL` and `EMBEDDING_DIM` in `.env`
- Switching models requires re-seeding (flush Redis DB or delete indexes)
