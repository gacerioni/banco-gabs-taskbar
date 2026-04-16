# 🔍 Redis Global Search — Taskbar Demo

**Customer 360 Global Search Demo** - Lightning-fast hybrid search (text + semantic) for banking routes, marketplace products, and financial services.

Built with **Redis 8 + RediSearch + RedisVL** for sub-second performance.

> 🇧🇷 **[Leia o guia completo em Português](GUIA-PT-BR.md)**

---

## 🎯 Features

- **🔍 Hybrid Search**: Text (exact + synonyms) + Vector (semantic)
- **📚 Synonym Expansion**: Auto-expands synonyms via `FT.SYNUPDATE`
  - `robaro` → `bloquear`, `roubo`, `roubaram`, `perdi` ✅
- **🧠 Semantic Understanding**: Handles typos and variations via embeddings
  - `robaro meu cartao` → finds "Bloquear Cartão" ✅
  - `mandar dinheiro` → finds "Pix" ✅
- **🎯 Intent Detection**: Automatically detects user intent (routes vs products)
- **⚡ Sub-second Performance**: ~40-80ms average latency
- **📦 Multi-Type Results**: Banking routes, marketplace SKUs, financial products
- **⌨️ Real-time Autocomplete**: 200ms debounce with keyboard navigation
- **🔌 Pluggable Embeddings**: Easy to swap models (OpenAI, HuggingFace, local)

---

## 🚀 Quick Start

### 1. Prerequisites

- **Python 3.9+**
- **Redis 8+** with RediSearch and RedisJSON modules
  - [Redis Cloud](https://redis.com/try-free/) (recommended, free tier available)
  - Or local: `brew install redis-stack` (macOS) / `docker run redis/redis-stack` (any OS)

### 2. Install Dependencies

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment

Create a `.env` file with your Redis connection:

```bash
# Redis Cloud (recommended)
REDIS_URL=redis://default:your-password@redis-xxxxx.cloud.redislabs.com:xxxxx

# Local Redis (no auth)
REDIS_URL=redis://localhost:6379/0
```

### 4. Start Server & Seed Data

```bash
# Start server
./run.sh  # or: uvicorn main:app --reload

# In another terminal, seed data
curl -X POST http://localhost:8000/seed
```

### 5. Open Browser

Visit **http://localhost:8000** and start searching!

Try: `robaro meu cartao` (with typo) → finds "Bloquear Cartão" ✅

---

## 📊 Architecture

### How It Works

```
User Query: "robaro meu cartao"
         ↓
┌────────────────────────────────┐
│ 1. Intent Detection            │
│    (RedisVL SemanticRouter)    │
│    → Result: "route"           │
└────────────────────────────────┘
         ↓
┌────────────────────────────────┐
│ 2. Hybrid Search               │
│    ┌─────────┐  ┌──────────┐  │
│    │ Text    │  │ Vector   │  │
│    │ (exact) │  │(semantic)│  │
│    └─────────┘  └──────────┘  │
│         └──────┬──────┘        │
│         Merge & Dedupe         │
└────────────────────────────────┘
         ↓
┌────────────────────────────────┐
│ 3. Intelligent Ranking         │
│    - Text score: 2.0           │
│    - Vector score: 0-1.5       │
│    - Intent boost              │
│    - Popularity boost          │
└────────────────────────────────┘
         ↓
    "Bloquear Cartão" ✅
```

### Redis Indexes

| Index | Prefix | Description | Fields |
|-------|--------|-------------|--------|
| `idx:routes` | `route:` | Banking actions | title, subtitle, keywords, aliases, embedding (384d) |
| `idx:skus` | `sku:` | Marketplace products | title, brand, price, cashback, embedding (384d) |
| `idx:products` | `product:` | Banking products | title, category, keywords, embedding (384d) |

### Embedding Model

**Current**: `paraphrase-multilingual-MiniLM-L12-v2` (384 dimensions)
- ✅ Multilingual (Portuguese support)
- ✅ Offline (no API calls)
- ✅ Fast inference (~10ms)

**Easy to swap**:
```python
# In main.py, change get_vectorizer():
_vectorizer = HFTextVectorizer(
    model="sentence-transformers/your-model-here"
)
```

---

## 🧪 Testing

### Run Tests

```bash
source .venv/bin/activate

# Test semantic similarity
python tests/test_embeddings.py

# Test end-to-end search
python tests/test_search_e2e.py

# Test intent detection
python tests/test_semantic_router.py

# Performance benchmark
python tests/benchmark.py
```

### Expected Performance

```
📈 BENCHMARK RESULTS
⏱️  Latency (Client + Server)
   Mean:    45ms
   p50:     42ms
   p95:     78ms
   p99:     95ms

📊 Result Distribution
   Routes:   45%
   SKUs:     38%
   Products: 17%
```

---

## 📁 Project Structure

```
redis-global-search-demo/
├── main.py              # FastAPI server + Redis logic
├── routes.jsonl         # 15 banking routes/actions
├── skus.jsonl           # 15 marketplace products
├── products.jsonl       # 10 banking products
├── requirements.txt     # Python dependencies
├── README.md            # This file
├── static/              # Frontend assets
│   ├── index.html       # Frontend UI
│   ├── styles.css       # Demo UI theme (orange)
│   └── app.js           # Search logic + autocomplete
└── tests/               # Tests and benchmarks
    ├── benchmark.py           # Performance testing script
    ├── test_semantic_router.py # Semantic routing tests
    ├── test_search_e2e.py     # End-to-end search tests
    └── test_embeddings.py     # Embedding function tests
```

---

## 🎯 Demo Queries

### Synonym Expansion (FT.SYNUPDATE)

| Query | Finds | Why |
|-------|-------|-----|
| `robaro` | Bloquear Cartão | Synonym of "bloquear" |
| `emprest` | Empréstimo | Synonym of "empréstimo" |
| `card` | Cartão Virtual | Synonym of "cartão" |

### Semantic Search (Embeddings 🔥)

| Query | Finds | Why |
|-------|-------|-----|
| `robaro meu cartao` | Bloquear Cartão | Synonym + context |
| `mandar dinheiro` | Pix | Semantic variation |
| `quanto gastei` | Extrato | Intent detection |
| `pagar conta de luz` | Pagar Boleto | Contextual match |

### Exact Matches (Text Search)

| Query | Finds |
|-------|-------|
| `pix` | Pix - Transferir dinheiro |
| `boleto` | Pagar Boleto |
| `extrato` | Extrato |
| `iphone` | iPhone 15 Pro Max |

---

## 🎨 UI Features

- **🎨 Demo UI theme**: Orange gradient (#FF7A00)
- **⚡ Real-time Autocomplete**: Dropdown with type badges
- **🎯 Typed Result Cards**: Different styling per type
- **🔘 Quick Access**: One-click common queries
- **📊 Debug Panel**: Latency, intent, result count

---

## 🔧 API Endpoints

### `POST /seed`
Load sample data into Redis

```bash
curl -X POST http://localhost:8000/seed
```

### `GET /search`
Search across all indexes

```bash
curl "http://localhost:8000/search?q=pix&lang=pt&country=BR&limit=10"
```

**Response:**
```json
{
  "tracking_id": "search_1738512345678",
  "latency_ms": 42,
  "query": "pix",
  "intent": "route",
  "total": 1,
  "results": [
    {
      "type": "route",
      "id": "route_001",
      "title": "Pix",
      "subtitle": "Transferir dinheiro na hora",
      "deep_link": "inter://pix/transfer",
      "score": 1.95
    }
  ]
}
```

### `GET /health`
Health check

---

## 🚧 Future Ideas

- [ ] Query highlighting in results
- [ ] User context (location, preferences) in ranking
- [ ] Multi-language support (en, es)
- [ ] Filters (category, price, stock)
- [ ] Click tracking & learning-to-rank
- [ ] Query caching for popular searches
- [ ] Voice search integration

---

## 📝 License

MIT License - Demo project for Redis Global Search

---

## 🤝 Contributing

Contributions welcome! Areas of interest:
- Embedding models
- Ranking algorithms
- UI/UX improvements
- Performance optimizations

---

**Built with ❤️ using Redis 8, FastAPI, and Vanilla JS**

> 🇧🇷 **[Guia completo em Português](GUIA-PT-BR.md)** - Instruções detalhadas de instalação e uso

