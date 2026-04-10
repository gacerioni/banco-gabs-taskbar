# 📁 Project Structure - Banco Inter Taskbar

## 🎯 Quick Navigation Guide

### 🔧 "I want to edit route examples (search vs chat)"
→ **`src/routers/route_examples/`**
- `pt_search.py` - Portuguese search examples
- `pt_chat.py` - Portuguese chat examples
- `en_search.py` - English search examples
- `en_chat.py` - English chat examples
- `es_search.py` - Spanish search examples
- `es_chat.py` - Spanish chat examples

### 📊 "I want to edit seed data (routes, products, SKUs)"
→ **`src/data/seed/`**
- `routes.jsonl` - Banking routes
- `products.jsonl` - Banking products
- `skus.jsonl` - Marketplace products

### 🧪 "I want to test the router interactively"
→ **`python tools/interactive_tester.py`**

### 📝 "I want to read documentation"
→ **`docs/`**
- `README.md` - Main README (English)
- `GUIA-PT-BR.md` - Full guide (Portuguese)
- `PROJECT_STRUCTURE.md` - This file

### 🔍 "I want to understand the code flow"
→ Read below 👇

---

## 📂 Complete Directory Structure

```
banco-inter-taskbar/
├── src/                                # 🔥 ALL SOURCE CODE HERE
│   ├── routers/                        # Language + Intent routing
│   │   ├── language_detector.py       # Detects PT/EN/ES
│   │   ├── intent_router.py           # Routes to search/chat
│   │   └── route_examples/            # 🎯 EDIT EXAMPLES HERE!
│   │       ├── pt_search.py           # PT search examples
│   │       ├── pt_chat.py             # PT chat examples
│   │       ├── en_search.py           # EN search examples
│   │       ├── en_chat.py             # EN chat examples
│   │       ├── es_search.py           # ES search examples
│   │       └── es_chat.py             # ES chat examples
│   │
│   ├── data/                           # Data layer
│   │   ├── seed/                      # 📊 SEED DATA HERE!
│   │   │   ├── routes.jsonl           # Banking routes
│   │   │   ├── skus.jsonl             # Marketplace products
│   │   │   └── products.jsonl         # Banking products
│   │   └── models/                    # Redis index schemas (TODO)
│   │
│   ├── core/                           # Core configs + models
│   │   ├── config.py                  # Configuration
│   │   └── models.py                  # Pydantic models
│   │
│   ├── search/                         # Search engine (TODO - refactor from main.py)
│   ├── chat/                           # Chat handler (TODO - refactor from chat_handler.py)
│   └── api/                            # API endpoints (TODO - refactor from main.py)
│
├── tools/                              # 🧰 CLI TOOLS
│   └── interactive_tester.py          # Interactive router tester
│
├── tests/                              # 🧪 ALL TESTS
│   ├── test_router_interactive.py
│   ├── test_semantic_router.py
│   └── test_*.py
│
├── docs/                               # 📚 DOCUMENTATION
│   ├── README.md                      # Main README
│   ├── GUIA-PT-BR.md                  # Portuguese guide
│   ├── SEMANTIC_ROUTER_IMPLEMENTATION.md
│   └── PROJECT_STRUCTURE.md           # This file
│
├── static/                             # Frontend
│   ├── index.html
│   ├── app.js
│   └── styles.css
│
├── config.py                           # Config (backward compat - symlink)
├── main.py                             # Entry point (TODO - refactor)
├── requirements.txt
└── run.sh
```

---

## 🔄 Code Flow

### 1. User makes a query: `"quero falar com o gerente"`

### 2. Language Detection
- **File**: `src/routers/language_detector.py`
- **Function**: `detect_language()`
- **Output**: `"pt"` (Portuguese detected)

### 3. Intent Routing
- **File**: `src/routers/intent_router.py`
- **Function**: `route_query()`
- **Uses examples from**: `src/routers/route_examples/pt_chat.py`
- **Output**: `("pt", "chat", 0.95)` - High confidence chat intent!

### 4. Execute based on intent
- **If "search"**: Execute hybrid search (text + vector)
- **If "chat"**: Execute chat handler (mock or OpenAI)

---

## 🎯 Common Tasks

### Task: Add new search example for Portuguese

1. Open: `src/routers/route_examples/pt_search.py`
2. Add to `PT_SEARCH_EXAMPLES` list:
   ```python
   "nova query de busca",
   ```
3. Done! Router will automatically use it.

### Task: Add new chat example for English

1. Open: `src/routers/route_examples/en_chat.py`
2. Add to `EN_CHAT_EXAMPLES` list:
   ```python
   "new chat query",
   ```
3. Done!

### Task: Add new seed route

1. Open: `src/data/seed/routes.jsonl`
2. Add new line:
   ```json
   {"id": "route_016", "title": "Nova Rota", "subtitle": "Descrição", ...}
   ```
3. Restart server and run `/seed`

### Task: Test routing interactively

```bash
python tools/interactive_tester.py
```

Type queries and see language + intent detection in real-time!

---

## 📦 Modules Explained

| Module | Purpose | Files |
|--------|---------|-------|
| **routers** | Language + intent routing | `language_detector.py`, `intent_router.py`, `route_examples/` |
| **data** | Seed data + Redis schemas | `seed/`, `models/` |
| **core** | Config + Pydantic models | `config.py`, `models.py` |
| **search** | Search engine logic | (TODO - refactor from main.py) |
| **chat** | Chat handler logic | (TODO - refactor from chat_handler.py) |
| **api** | FastAPI endpoints | (TODO - refactor from main.py) |

---

## 🚀 Next Steps (TODO)

- [ ] Refactor `main.py` into `src/api/`
- [ ] Refactor `chat_handler.py` into `src/chat/`
- [ ] Refactor search logic into `src/search/`
- [ ] Create Redis index schemas in `src/data/models/`
- [ ] Update imports everywhere

---

**Now you can easily find and edit everything!** 🎉

