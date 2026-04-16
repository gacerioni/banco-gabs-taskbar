# 🔀 Semantic Router Implementation - Stack C

## 📋 Overview

Implementação de roteador semântico multilíngue para o Redis Global Search demo usando **Stack C**:

```
Stack C: MiniLM router + Qwen3 search
- Language Detection: xlm-roberta-base-language-detection (125M params, 768 dims)
- Semantic Router: paraphrase-multilingual-MiniLM-L12-v2 (118M params, 384 dims)
- Search Embeddings: gte-Qwen2-1.5B-instruct (1.5B params, 4096 dims)
```

---

## 🏗️ Arquitetura

```
User Query: "como faço pra investir em CDB?"
         ↓
┌─────────────────────────────────────┐
│ 1. Language Detection (~5ms)        │
│    xlm-roberta-base-lang-detection  │
│    → Result: "pt"                   │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│ 2. Semantic Router (~15ms)          │
│    MiniLM-L12-v2 (384 dims)         │
│    RedisVL SemanticRouter           │
│                                     │
│    Routes (PT-specific):            │
│    - "search" (produtos/rotas)      │
│    - "chat" (conversação/ajuda)     │
│                                     │
│    → Result: "chat" (0.89 conf)     │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│ 3A. Chat Route                      │
│     - Mock: "Abrindo chat..."       │
│     - OpenAI: gpt-4o-mini           │
│     - Response conversacional       │
└─────────────────────────────────────┘
         OR
┌─────────────────────────────────────┐
│ 3B. Search Route                    │
│     - Qwen3 embeddings (4096 dims)  │
│     - FT.SEARCH (text + vector)     │
│     - Return produtos/rotas         │
└─────────────────────────────────────┘
```

---

## 📁 Arquivos Criados

```
redis-global-search-demo/
├── router_config.py          # Configuração de rotas e detecção de idioma
├── semantic_router.py         # Roteador semântico principal
├── chat_handler.py            # Handler de chat (mock + OpenAI)
├── test_semantic_router.py    # Testes automatizados
└── SEMANTIC_ROUTER_IMPLEMENTATION.md  # Esta documentação
```

---

## 🚀 Como Usar

### 1. Instalar Dependências

```bash
pip install -r requirements.txt
```

Novas dependências adicionadas:
- `transformers>=4.36.0` - Para language detection
- `torch>=2.1.0` - Backend do transformers
- `openai>=1.10.0` - Para chat responses

### 2. Configurar Variáveis de Ambiente (Opcional)

```bash
# .env
OPENAI_API_KEY=sk-xxx  # Opcional: para chat real com IA
```

### 3. Testar o Router

```bash
python test_semantic_router.py
```

Espere ver:
- ✅ Testes de detecção de idioma (PT/EN/ES)
- ✅ Testes de roteamento semântico (search vs chat)
- ✅ Success rate > 90%

### 4. Usar a API

#### Endpoint Novo: `/api/search`

```bash
# Search intent (PT)
curl "http://localhost:8000/api/search?q=pix"

# Chat intent (PT)
curl "http://localhost:8000/api/search?q=como%20funciona%20o%20pix?"

# Chat com OpenAI
curl "http://localhost:8000/api/search?q=como%20funciona%20o%20pix?&use_openai=true"

# English
curl "http://localhost:8000/api/search?q=how%20do%20I%20invest?"

# Spanish  
curl "http://localhost:8000/api/search?q=necesito%20ayuda"
```

#### Endpoint Legado: `/search`

Continua funcionando normalmente (backward compatible).

---

## 📊 Resposta da API

### Search Intent

```json
{
  "tracking_id": "unified_1234567890",
  "latency_ms": 45.23,
  "query": "pix",
  "language": "pt",
  "intent": "search",
  "confidence": 0.95,
  "total": 1,
  "results": [
    {
      "type": "route",
      "id": "route_001",
      "title": "Pix",
      "subtitle": "Transferir dinheiro na hora"
    }
  ]
}
```

### Chat Intent

```json
{
  "tracking_id": "unified_1234567891",
  "latency_ms": 1250.45,
  "query": "como funciona o pix?",
  "language": "pt",
  "intent": "chat",
  "confidence": 0.89,
  "chat_response": "O Pix é um sistema de pagamentos instantâneos...",
  "chat_provider": "openai",
  "chat_model": "gpt-4o-mini"
}
```

---

## 🧪 Testes

### Test Cases Incluídos

- ✅ 15+ queries em Português (search + chat)
- ✅ 6+ queries em Inglês (search + chat)
- ✅ 4+ queries em Espanhol (search + chat)

### Executar Testes

```bash
# Teste do router
python test_semantic_router.py

# Teste end-to-end da API
curl -X POST http://localhost:8000/seed  # Seed data first
python test_search_e2e.py
```

---

## ⚙️ Configuração

### Modelos Usados

Configurados em `config.py`:

```python
# Language Detection
LANGUAGE_MODEL = "papluca/xlm-roberta-base-language-detection"

# Semantic Router (leve, rápido)
ROUTER_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
ROUTER_DIM = 384

# Search Embeddings (poderoso, Magalu-style)
EMBEDDING_MODEL = "Alibaba-NLP/gte-Qwen2-1.5B-instruct"
EMBEDDING_DIM = 4096

# Chat
OPENAI_MODEL = "gpt-4o-mini"
```

### Customizar Rotas

Edite `router_config.py`:

```python
PT_SEARCH_REFERENCES = [
    # Adicione novos termos de busca
    "novo termo",
]

PT_CHAT_REFERENCES = [
    # Adicione novas queries de chat
    "nova pergunta?",
]
```

---

## 📈 Performance Esperada

| Componente | Latência | Memória |
|------------|----------|---------|
| Language Detection | ~5ms | ~500MB |
| Semantic Router | ~15ms | ~500MB |
| Search (Qwen3) | ~50ms | ~6GB |
| Chat (OpenAI) | ~1000ms | - |
| **Total (search)** | **~70ms** | **~7GB** |
| **Total (chat)** | **~1020ms** | **~1GB** |

---

## 🎯 Próximos Passos

- [ ] Integrar com UI (frontend atualizado)
- [ ] Adicionar mais idiomas (FR, DE, IT)
- [ ] Melhorar rotas com exemplos de produção
- [ ] Adicionar tracking de clicks
- [ ] A/B testing search vs chat distribution
- [ ] Implementar FT.HYBRID nativo (Redis 8.6+)

---

**Desenvolvido com ❤️ usando Redis 8, RedisVL, e Qwen3**

