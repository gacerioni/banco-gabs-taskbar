# Redis 8.6 HYBRID Search Configuration

## 🔥 What is HYBRID Search?

Redis 8.6+ introduces **native HYBRID scoring** that combines:

1. **FTS (Full-Text Search)** - Traditional keyword matching with weighted fields
2. **VSS (Vector Similarity Search)** - Semantic similarity using embeddings

All scoring happens **NATIVELY in Redis** - no Python post-processing needed!

---

## ⚙️ Configuration

### Environment Variables (.env)

```bash
# Hybrid Search Weights
FTS_WEIGHT=0.7  # 70% text relevance (keyword matching)
VSS_WEIGHT=0.3  # 30% semantic similarity (vector distance)
```

### Field Weights (in schema files)

**Routes** (`src/data/models/route_schema.py`):
```python
FIELD_WEIGHTS = {
    "title": 10.0,      # Highest priority
    "subtitle": 5.0,    # High priority
    "description": 1.0, # Base weight
    "tags": 3.0,        # Medium priority
}
```

**Products** (`src/data/models/product_schema.py`):
```python
FIELD_WEIGHTS = {
    "title": 10.0,
    "subtitle": 5.0,
    "description": 2.0,  # More important than routes
    "benefits": 3.0,
    "tags": 4.0,
}
```

**SKUs** (`src/data/models/sku_schema.py`):
```python
FIELD_WEIGHTS = {
    "title": 10.0,
    "brand": 7.0,        # Brand very important for marketplace
    "category": 5.0,
    "description": 2.0,
    "tags": 4.0,
}
```

---

## 🎯 How It Works

### 1. Query Processing

```
User query: "pix para amigo"
    ↓
Language Detection: PT
    ↓
Intent Routing: SEARCH (vs CHAT)
    ↓
Hybrid Search
```

### 2. Dual Scoring

**FTS Score (70%)**:
- Matches keywords: "pix", "amigo"
- Weighted by field importance
- Applies synonyms
- BM25 algorithm

**VSS Score (30%)**:
- Embeds query with Qwen3 → 4096-dim vector
- Finds nearest vectors (COSINE distance)
- Semantic similarity

**Final Score = (FTS_score × 0.7) + (VSS_score × 0.3)**

### 3. Native Redis Command

```redis
FT.SEARCH idx:routes 
  "@lang:{pt} @country:{BR} pix para amigo"
  DIALECT 4
  PARAMS 6
    fts_weight 0.7
    vss_weight 0.3
    query_vector <4096-dim vector bytes>
  SCORER HYBRID
  SORTBY _score DESC
  LIMIT 0 10
```

---

## 🔧 Tuning Guide

### Scenario 1: Users prefer exact matches
```bash
FTS_WEIGHT=0.9  # 90% keyword matching
VSS_WEIGHT=0.1  # 10% semantic
```

### Scenario 2: Users search conceptually
```bash
FTS_WEIGHT=0.5  # 50% keywords
VSS_WEIGHT=0.5  # 50% semantic
```

### Scenario 3: Production balanced (default)
```bash
FTS_WEIGHT=0.7  # 70% keywords
VSS_WEIGHT=0.3  # 30% semantic
```

---

## 📊 Performance

**Latency:**
- FTS: ~5-10ms
- VSS: ~20-30ms (4096-dim vectors)
- **HYBRID: ~30-40ms** (parallel execution in Redis)

**Quality:**
- FTS alone: Good for exact matches, poor for synonyms
- VSS alone: Good for concepts, poor for specific terms
- **HYBRID: Best of both worlds** 🎯

---

## 🎨 Index Schema Example

```python
# From src/data/models/route_schema.py

FT.CREATE idx:routes
  ON JSON
  PREFIX 1 route:
  SCHEMA
    title TEXT WEIGHT 10.0
    subtitle TEXT WEIGHT 5.0
    description TEXT WEIGHT 1.0
    tags TAG SEPARATOR ","
    type TAG
    lang TAG
    country TAG
    embedding VECTOR FLAT 6
      TYPE FLOAT32
      DIM 4096
      DISTANCE_METRIC COSINE
```

---

## 🚀 Usage in Code

```python
from src.search.hybrid_search import hybrid_search
from src.data import get_redis_client

redis_client = get_redis_client()

results = hybrid_search(
    redis_client=redis_client,
    query="pix para amigo",
    lang="pt",
    country="BR",
    limit=10,
    fts_weight=0.7,  # Optional override
    vss_weight=0.3   # Optional override
)
```

---

## 📚 References

- [Redis Stack Documentation](https://redis.io/docs/stack/)
- [RediSearch HYBRID Scoring](https://redis.io/docs/stack/search/reference/scoring/)
- [Vector Similarity Search](https://redis.io/docs/stack/search/reference/vectors/)

---

**Pro tip:** Monitor query latency and adjust weights based on user feedback!

