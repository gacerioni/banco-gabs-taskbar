# Testing: Banco Inter Global TaskBar

## Overview
FastAPI app with vanilla JS frontend for banking search. Uses Redis 8.4+ FT.HYBRID for hybrid FTS+VSS search, semantic routing, autocomplete, synonyms, and spellcheck.

## Prerequisites
- Python 3.12+
- Redis 8.4+ with FT.HYBRID support (Redis Cloud or local)
- ~500MB disk for MiniLM model download on first run

## Devin Secrets Needed
- `REDIS_URL` — Redis Cloud connection string (e.g. `redis://default:<password>@<host>:<port>`)

## Setup
1. Create `.env` in repo root with `REDIS_URL=<your redis url>`
2. Run `./run.sh` — this creates a venv, installs deps, and starts the FastAPI server at `http://localhost:8000`
3. First run auto-seeds 115 docs (35 routes, 25 products, 55 SKUs) if indexes don't exist
4. MiniLM model (~120MB) downloads on first embedding call, takes ~2-5s to load
5. Language detection model (~1.1GB) downloads on first search, takes ~5s

## Key Test Flows

### 1. Exact match search
- Search "pix" → Pix should be #1 result with exact match boost
- Verify debug panel shows Language=PT, Intent=SEARCH

### 2. Semantic search
- Search "mandar dinheiro" (send money) → Pix should appear in top results
- This proves VSS (vector) search is working alongside FTS

### 3. Chat intent detection
- Search "como funciona o pix?" → Should detect CHAT intent
- UI shows purple gradient card with "Resposta do Chat" header
- Mock response shown unless OPENAI_API_KEY is configured

### 4. Query caching
- Search same term twice
- First: `breakdown.cache_hit: false`, higher latency
- Second: `breakdown.cache_hit: true`, much lower latency

### 5. API response fields
- `breakdown` object: `embedding_ms`, `redis_search_ms`, `post_processing_ms`, `spellcheck_ms`, `total_redis_ms`, `cache_hit`
- Each result has `match_explanation` string (e.g. "Keyword: 'pix' | Exact title match (10x boost) | RRF score: 0.1484 | Type: route")
- `did_you_mean` and `spellcheck_suggestions` appear when search returns 0 results

## Gotchas
- First search after startup is slow (~10-15s) because it loads language detection + semantic router models
- Subsequent searches are fast (~100-300ms, or <10ms for cache hits)
- If switching embedding models (MiniLM ↔ Qwen), existing Redis data must be re-seeded (dimension mismatch)
- `run.sh` uses uvicorn with `--reload`, so code changes auto-restart the server
- The `redis_search_ms` in breakdown measures wall-clock time including JSON.GET round-trips, while `total_redis_ms` is only FT.HYBRID command time
- Quick access buttons in UI: Pix, Boleto, Fatura, Investir, iPhone, Notebook, Empréstimo, Seguros
- DevTools Network tab is useful for inspecting `breakdown` and `match_explanation` fields since the frontend doesn't display them directly

## Frontend
- Vanilla JS at `static/app.js`, calls `/api/search?q=...&limit=20`
- Debug panel ("Performance & Debug Info") shows language, intent, confidence, server/Redis latency
- Banco Inter orange theme (#FF7A00)
