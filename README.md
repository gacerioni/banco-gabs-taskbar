# Redis Global Search — Taskbar & Concierge Demo

This repository is a **hands-on evaluation demo** of how **Redis 8** can power a single **global search bar** (banking routes, marketplace products, and SKU inventory) **and** a **conversational assistant** that still grounds answers in the same search index and keeps state in Redis.

> **[Leia o guia em Português](README-PTBR.md)**

---

## What this demo is for (customer view)

Organizations often split **“find a screen or product”** (search) from **“talk to an assistant”** (chat). In practice, users blur those behaviors in one box. This demo shows **one Redis-backed surface** that:

1. **Hybrid global search** — Full-text (with synonyms and typo-tolerant behavior) **plus** semantic (vector) search over sample **banking routes**, **catalog products**, and **SKUs**, with **sub-second** response times typical of Redis Search & Query.
2. **Intent routing** — The same query stream is classified (via **RedisVL** semantic routing) as **search** (navigate / discover) vs **chat** (conversational).
3. **Concierge with real inventory tools** — In **chat** mode, an optional **OpenAI** tool-calling flow searches **SKU inventory only** through the **same hybrid index** the taskbar uses—so the assistant does not invent SKUs. It can **add items to a shopping cart** stored in Redis under `demo:cart:{session_id}`.
4. **Grounded FAQ + short memory** — A small **FAQ** set lives in Redis with embeddings aligned to the search embedding model; top matches inform the concierge system prompt. **Short-term chat history** is stored with **LangChain** `RedisChatMessageHistory` so follow-up turns stay coherent without a separate chat database.
5. **Operator workflow** — An **Admin** UI supports indexing new content and **hot reload** so autocomplete and search stay in sync after changes.

**Without** an `OPENAI_API_KEY`, the UI still demonstrates **deterministic concierge behavior**: hybrid SKU preview from Redis and live cart readout, so stakeholders can see the data path without enabling GPT.

In short: **Redis is the system of record for indexes, vectors, autocomplete, cart, FAQ embeddings, and recent chat**—search and assistant stay aligned.

---

## What you will see in the browser

| Area | What to try |
|------|----------------|
| **Taskbar** | Queries like `robaro meu cartao` (typo) → **Bloquear Cartão**; `mandar dinheiro` → **Pix**; `iphone` → **iPhone** SKUs. Watch **autocomplete** and instant hybrid results. |
| **Chat / concierge** | Portuguese examples such as *“quero adicionar um iphone ao carrinho”*. With **OpenAI** enabled in the taskbar toggle, the model uses **tools** that hit Redis; the **cart** updates in Redis and reflects in the API response. |
| **Admin** | Open `/admin` to add routes/SKUs and exercise **hot reload** after content changes. |

Unified API for integrations: `GET /api/search?q=...&session_id=<uuid>&use_openai=true|false` — preserve `session_id` across calls so **cart** and chat context stay consistent.

---

## Technical highlights (for builders)

- **Redis 8** with **RediSearch** + **RedisJSON** / **RedisVL** patterns as used in the codebase (hybrid **FTS + VSS** weights configurable via env).
- **Synonyms** (`FT.SYNUPDATE`), **autocomplete** (`FT.SUGGET`, prefix `ac:global_search`).
- **Semantic intent router** per language (`pt`, `en`, `es`) with pre-warmed models on startup.
- **Key prefixes (demo):** cart `demo:cart:{session_id}`; FAQ `demo:concierge:faq`; STM index `idx:demo_stm_chat` / prefix `demo:stm`. Tunables: `CONCIERGE_FAQ_TOP_K`, `CONCIERGE_STM_MAX_MESSAGES`. Edit `src/data/seed/concierge_faq.json` and run **`POST /seed`** to refresh FAQ content.
- **Debug:** `DEBUG=true` can include `tool_trace` in JSON for demos and troubleshooting.

---

## Quick start (Docker Compose)

### Prerequisites

- **Docker** and **Docker Compose**
- **Redis 8+** with Search/JSON (and modules your deployment expects)—e.g. [Redis Cloud](https://redis.com/try-free/) or **Redis Stack** locally.

### Configure

Create a `.env` in the project root:

```bash
REDIS_URL=redis://default:your-password@your-host:6379/0
# Optional:
# OPENAI_API_KEY=sk-...
# DEBUG=false
# APP_PORT=8000
```

### Run

```bash
docker compose up -d --build
```

Open **http://localhost:8000** (or the host port you mapped with `APP_PORT`).

### Run a pre-built image only

If you already have Redis reachable from the container:

```bash
docker run --rm -it -p 8000:8000 \
  -e REDIS_URL='redis://default:PASSWORD@HOST:6379/0' \
  -e OPENAI_API_KEY='sk-...' \
  -e DEBUG=false \
  gacerioni/gabs-global-search-concierge-redis:latest
```

### First run and “from scratch”

On startup, if required **indexes are missing**, the app **creates indexes, seeds sample data**, applies synonyms, builds autocomplete, and pre-warms routers (see `main.py` lifespan). For a **clean** first-time experience, point `REDIS_URL` at an **empty logical database** (or a dedicated Redis URL). To **force a full data reload** after content or FAQ changes, use:

```bash
curl -X POST http://localhost:8000/seed
```

Health: `GET http://localhost:8000/health`

---

## Manual install (no Docker)

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# Set REDIS_URL in .env, then:
./run.sh
```

---

## Further reading

- **[docs/](docs/)** — architecture and hybrid search notes (`REDIS_8.6_HYBRID_SEARCH.md`, semantic router, project structure).

Enjoy exploring **Redis 8** as the backbone for **unified search + concierge + state** in a financial / marketplace UX.
