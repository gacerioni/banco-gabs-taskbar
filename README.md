# 🏦 Banco Inter Task Bar MVP

**Global Search for Customer 360** - Fast hybrid search (text + vector) for routes, marketplace SKUs, and banking products.

Built with **Redis 8 + RediSearch + RedisVL** for sub-second performance.

---

## 🎯 Features

- **Hybrid Search**: Text (full-text) + Vector (semantic) search
- **Multi-Type Results**: Routes (banking actions), SKUs (marketplace products), Banking Products
- **Intent Detection**: Automatically detects if user wants routes vs products
- **Real-time Autocomplete**: 200ms debounce with keyboard navigation
- **Sub-second Performance**: Optimized for low latency (tens of ms Redis-side)
- **Pluggable Embeddings**: Easy to swap embedding providers (OpenAI, HuggingFace, etc.)

---

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.9+
- Redis 8+ with RediSearch and RedisJSON modules (or Redis Cloud)

### 2. Install Dependencies

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment

Copy the example environment file and configure your Redis connection:

```bash
cp .env.example .env
```

Edit `.env` and set your Redis URL:

```bash
# Local Redis (no authentication)
REDIS_URL=redis://localhost:6379/0

# Redis Cloud (with authentication)
REDIS_URL=redis://default:your-password@redis-12345.cloud.redislabs.com:12345

# Redis Cloud with SSL
REDIS_URL=rediss://default:your-password@redis-12345.cloud.redislabs.com:12345
```

### 4. Start Server

**Option A: Using the run script (recommended)**
```bash
./run.sh
```

**Option B: Manual start**
```bash
source .venv/bin/activate
uvicorn main:app --reload
```

### 5. Seed Data

```bash
# In another terminal or browser
curl -X POST http://localhost:8000/seed

# Or visit http://localhost:8000/seed in your browser
```

### 6. Open Browser

Visit **http://localhost:8000** and start searching!

---

## 📊 Architecture

### Redis Schema

**Three indexes:**

1. **`idx:routes`** - Banking actions (Pix, boleto, fatura, etc.)
   - Prefix: `route:`
   - Fields: title, subtitle, description, keywords, aliases, category, lang, country, popularity, embedding

2. **`idx:skus`** - Marketplace products (iPhone, TV, notebook, etc.)
   - Prefix: `sku:`
   - Fields: title, subtitle, description, keywords, brand, category, subcategory, price, cashback, popularity, in_stock, embedding

3. **`idx:products`** - Banking products (CDB, Tesouro, Seguros, etc.)
   - Prefix: `product:`
   - Fields: title, subtitle, description, keywords, aliases, category, lang, country, popularity, embedding

### Search Flow

```
User Query
    ↓
Intent Detection (route vs sku vs mixed)
    ↓
Text Search (FT.SEARCH) across all indexes
    ↓
Apply Intent-Based Boosting
    ↓
Re-rank by: text_score + popularity + intent_boost
    ↓
Return Typed Results (with deep_link/url)
```

### Embedding Strategy

- **Default**: Stub embeddings (hash-based, deterministic)
- **Production**: Swap with real embeddings:
  - OpenAI: `text-embedding-3-small` (1536 dims)
  - HuggingFace: `sentence-transformers/all-MiniLM-L6-v2` (384 dims)
  - Local: Any sentence-transformers model

**To swap embedding function:**

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')

def embed_real(text: str) -> np.ndarray:
    return model.encode(text, normalize_embeddings=True)

set_embedding_function(embed_real)
```

---

## 🧪 Testing & Benchmarks

Run performance tests:

```bash
python tests/benchmark.py
```

Run semantic router tests:

```bash
python tests/test_semantic_router.py
```

Run end-to-end search tests:

```bash
python tests/test_search_e2e.py
```

**Sample output:**

```
📈 BENCHMARK RESULTS
⏱️  LATENCY (Total: Client + Server)
   Mean:  45.23ms
   Median (p50): 42.10ms
   p95:   78.50ms
   p99:   95.20ms

📊 RESULT TYPE DISTRIBUTION
   route     : 450 (45.0%)
   sku       : 380 (38.0%)
   product   : 170 (17.0%)

🎯 INTENT DISTRIBUTION
   route     :  35 (35.0%)
   sku       :  40 (40.0%)
   mixed     :  25 (25.0%)
```

---

## 📁 Project Structure

```
banco-inter-taskbar/
├── main.py              # FastAPI server + Redis logic
├── routes.jsonl         # 15 banking routes/actions
├── skus.jsonl           # 15 marketplace products
├── products.jsonl       # 10 banking products
├── requirements.txt     # Python dependencies
├── README.md            # This file
├── static/              # Frontend assets
│   ├── index.html       # Frontend UI
│   ├── styles.css       # Banco Inter theme (orange)
│   └── app.js           # Search logic + autocomplete
└── tests/               # Tests and benchmarks
    ├── benchmark.py           # Performance testing script
    ├── test_semantic_router.py # Semantic routing tests
    ├── test_search_e2e.py     # End-to-end search tests
    └── test_embeddings.py     # Embedding function tests
```

---

## 🎯 Demo Search Queries

Try these queries to see the power of hybrid search:

### Exact Matches (Text Search)
- `pix` - Instant transfer
- `boleto` - Bill payment
- `extrato` - Account statement
- `investimentos` - Investments

### Semantic Search (AI-powered) 🔥
- `robaro meu cartao` → finds "Bloquear Cartão" (typo + variation)
- `me roubaram` → finds "Bloquear Cartão" (synonym)
- `perdi meu cartao` → finds "Bloquear Cartão" (alias)
- `quero investir` → finds "Investimentos" (intent)
- `mandar dinheiro` → finds "Pix" (alias)
- `pagar conta de luz` → finds "Pagar Boleto" (context)
- `quanto gastei` → finds "Extrato" (intent)
- `dinheiro de volta` → finds "Cashback" (synonym)

### Marketplace Products
- `iphone` - Apple smartphones
- `samsung galaxy` - Samsung phones
- `notebook` - Laptops
- `fone bluetooth` - Bluetooth headphones

### Mixed Intent
- `comprar iphone com pix` - Shows both SKU + route
- `investir em iphone` - Ambiguous query

---

## 🎨 UI Features

- **Banco Inter Branding**: Orange gradient theme (#FF7A00)
- **Real-time Autocomplete**: Dropdown with type badges (route/sku/product)
- **Typed Result Cards**: Different styling for routes vs products
- **Quick Access Buttons**: One-click search for common queries
- **Performance Stats**: Collapsible debug panel with latency, intent, result count

---

## 🔧 API Endpoints

### `POST /seed`
Load data from JSONL files into Redis

**Response:**
```json
{
  "status": "success",
  "counts": {
    "routes": 15,
    "skus": 15,
    "products": 10
  }
}
```

### `GET /search?q={query}&lang=pt&country=BR&limit=10`
Search across all indexes

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
      "icon": "💸",
      "category": "payments",
      "score": 1.95,
      "highlights": []
    }
  ]
}
```

### `GET /health`
Health check

---

## 🚧 Future Enhancements

- [ ] Add vector search fallback when text search returns < limit results
- [ ] Implement query highlighting in results
- [ ] Add user context (location, preferences) to ranking
- [ ] Support multi-language (en, es)
- [ ] Add filters (category, price range, in_stock)
- [ ] Implement click tracking and learning-to-rank
- [ ] Add Redis caching layer for popular queries
- [ ] Support voice search (speech-to-text)

---

## 📝 License

MIT License - Built for Banco Inter Customer 360 initiative

---

## 🤝 Contributing

This is an MVP. Contributions welcome for:
- Better embedding models
- Advanced ranking algorithms
- UI/UX improvements
- Performance optimizations

---

**Built with ❤️ using Redis 8, FastAPI, and Vanilla JS**

