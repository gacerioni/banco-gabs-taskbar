# Testing: Redis Global Search Taskbar

## Overview
FastAPI app with Redis 8.4+ hybrid search (FT.HYBRID), semantic routing, autocomplete, and query caching. Frontend is vanilla JS served at `/`.

## Devin Secrets Needed
- `REDIS_URL` — Redis Cloud connection string (redis:// or rediss://). Must be Redis 8.4+ with FT.HYBRID support.

## Setup
1. Create `.env` with `REDIS_URL=<your Redis Cloud URL>` (only required variable)
2. Start app: `source .env && ./run.sh`
3. Wait for pre-warming (~10s): look for `Server ready! First search will be fast.`
4. App available at `http://localhost:8000`

## Key Endpoints
- `GET /api/search?q=<query>&limit=<n>` — Unified search with semantic routing
- `GET /search?q=<query>&limit=<n>` — Legacy search (no routing)
- `GET /autocomplete?q=<prefix>&limit=<n>` — Autocomplete suggestions
- `GET /admin/api/routes` / `products` / `skus` — List items
- `POST /admin/api/routes` / `products` / `skus` — Create items
- `PUT /admin/api/routes/{id}` / `products/{id}` / `skus/{id}` — Update items
- `DELETE /admin/api/routes/{id}` / `products/{id}` / `skus/{id}` — Delete items
- `GET /admin/api/router-examples` — List semantic router examples
- `POST /admin/api/router-examples` — Add router example (hot reload)
- `DELETE /admin/api/router-examples/{id}` — Delete router example (hot reload)

## Testing Search Performance
- First search after startup should be <1000ms (models pre-warmed)
- Second identical search should be <300ms (cache hit, `breakdown.cache_hit: true`)
- No `Initializing semantic router` logs should appear during search requests
- All router initialization should happen at startup

## Testing Cache Invalidation
To verify cache invalidation works after admin writes:
1. Search for something (e.g., `q=PlayStation`) — note `cache_hit: false`
2. Search again — verify `cache_hit: true`
3. Create/update/delete any item via admin API
4. Search again — verify `cache_hit: false` (cache was invalidated)
5. Server logs should show `Invalidated N cached search results`

## Testing Semantic Routing
- Search queries (e.g., "Pix", "emprestimo") → intent: `search`
- Chat queries (e.g., "como funciona o pix?") → intent: `chat`
- Language detection: Portuguese, English, Spanish supported
- Router hot-reload: adding/deleting router examples via admin API takes effect immediately

## Common Issues
- If search is slow (>2s), check that models are pre-warmed at startup (look for `All models pre-warmed` log)
- If `Initializing semantic router` appears during search, the router overwrite logic may be broken
- The app auto-seeds Redis indexes if they don't exist on startup
- Switching embedding models (MiniLM ↔ Qwen) requires flushing Redis or re-seeding
- Default model is MiniLM (384 dims, ~2s load). Qwen (4096 dims) available via EMBEDDING_MODEL env var

## Dataset
- 35 routes (banking services like Pix, loans, card blocking)
- 25 products (financial products like mortgages, insurance)
- 55 SKUs (marketplace items like electronics, appliances)
- 800+ semantic router examples across 3 languages (pt/en/es)
