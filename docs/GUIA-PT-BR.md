# 🏦 Banco Inter - Busca Global Taskbar

## 📋 Índice
- [Sobre o Projeto](#sobre-o-projeto)
- [Objetivo da Demo](#objetivo-da-demo)
- [Tecnologias Utilizadas](#tecnologias-utilizadas)
- [Como Funciona](#como-funciona)
- [Instalação do Zero](#instalação-do-zero)
- [Testando a Aplicação](#testando-a-aplicação)
- [Exemplos de Busca](#exemplos-de-busca)

---

## 🎯 Sobre o Projeto

Esta é uma **demo de busca global** para o conceito de **Customer 360** do Banco Inter. O sistema permite que usuários busquem de forma inteligente por:

- **Rotas bancárias** (ações como Pix, boleto, extrato, investimentos)
- **Produtos do marketplace** (iPhone, notebook, TV, fones)
- **Produtos bancários** (CDB, Tesouro Direto, seguros)

A busca é **híbrida**, combinando:
- **Busca textual** (matches exatos + expansão de sinônimos)
- **Busca semântica** (entende variações e typos via embeddings)

### Por que isso é importante?

Imagine um usuário digitando:
- ❌ "robaro meu cartao" (com typo)
- ✅ O sistema entende e retorna "Bloquear Cartão"

Ou então:
- ❌ "mandar dinheiro"
- ✅ O sistema entende e retorna "Pix"

Isso é possível graças à **busca semântica com embeddings**!

---

## 🎯 Objetivo da Demo

Demonstrar como construir uma **busca global de alta performance** usando:

1. **Redis 8** como banco de dados vetorial e de busca
2. **RediSearch** para busca full-text
3. **RedisVL** para busca vetorial (embeddings)
4. **FastAPI** como backend Python
5. **Vanilla JavaScript** no frontend (sem frameworks!)

### Características principais:

- ⚡ **Sub-segundo**: Respostas em ~40-80ms
- 🧠 **Inteligente**: Expansão de sinônimos + busca semântica (typos e variações)
- 🎯 **Detecção de intenção**: Sabe se você quer uma rota ou produto
- 🔄 **Autocomplete em tempo real**: Sugestões enquanto você digita
- 📊 **Multi-tipo**: Busca em rotas, SKUs e produtos simultaneamente

---

## 🛠️ Tecnologias Utilizadas

### Backend
- **Python 3.9+**
- **FastAPI** - Framework web moderno e rápido
- **Redis 8** - Banco de dados com módulos RediSearch e RedisJSON
- **RedisVL** - Biblioteca para busca vetorial
- **sentence-transformers** - Modelos de embeddings multilíngues

### Frontend
- **HTML5 + CSS3** - Interface responsiva
- **Vanilla JavaScript** - Sem dependências de frameworks
- **Tema Banco Inter** - Gradiente laranja (#FF7A00)

### Infraestrutura
- **Redis Cloud** - Redis gerenciado (ou local)
- **Uvicorn** - Servidor ASGI para FastAPI

---

## 🔍 Como Funciona

### 1. Arquitetura de Busca

```
Usuário digita "robaro meu cartao"
         ↓
┌────────────────────────────────┐
│ 1. Detecção de Intenção        │
│    (RedisVL SemanticRouter)    │
│    → Resultado: "route"        │
└────────────────────────────────┘
         ↓
┌────────────────────────────────┐
│ 2. Busca Híbrida               │
│    ┌─────────────────────────┐ │
│    │ Texto (FT.SEARCH)       │ │
│    │ - Matches exatos        │ │
│    │ - Expansão de sinônimos │ │
│    │ - Prefix matching       │ │
│    └─────────────────────────┘ │
│              +                 │
│    ┌─────────────────────────┐ │
│    │ Vetorial (KNN)          │ │
│    │ - Similaridade semântica│ │
│    │ - Typos e variações     │ │
│    └─────────────────────────┘ │
│              ↓                 │
│       Mescla & Deduplica       │
└────────────────────────────────┘
         ↓
┌────────────────────────────────┐
│ 3. Ranking Inteligente         │
│    - Score textual: 2.0        │
│    - Score vetorial: 0-1.5     │
│    - Boost por intenção        │
│    - Boost por popularidade    │
└────────────────────────────────┘
         ↓
    "Bloquear Cartão" ✅
```

### 2. Expansão de Sinônimos (FT.SYNUPDATE)

O Redis expande automaticamente sinônimos durante a busca textual:

**Exemplos configurados:**
- `"robaro"` → `"bloquear"`, `"roubo"`, `"roubaram"`, `"perdi"`
- `"emprest"` → `"empréstimo"`, `"emprestimo"`, `"emprestim"`
- `"cartao"` → `"cartão"`, `"card"`

Quando você busca por `"robaro"`, o Redis automaticamente busca por **todos os sinônimos** do grupo!

### 3. Embeddings Semânticos

O sistema usa o modelo **paraphrase-multilingual-MiniLM-L12-v2** que:
- Entende português brasileiro
- Gera vetores de 384 dimensões
- Calcula similaridade entre textos
- Funciona offline (sem APIs externas)
- Captura variações que sinônimos não cobrem





---

## 🚀 Instalação do Zero

### Pré-requisitos

Antes de começar, você precisa ter instalado:

1. **Python 3.9 ou superior**
   ```bash
   python3 --version  # Deve mostrar 3.9+
   ```

2. **Redis 8+ com módulos RediSearch e RedisJSON**

   **Opção A: Redis Cloud (Recomendado - Mais Fácil)**
   - Acesse [Redis Cloud](https://redis.com/try-free/)
   - Crie uma conta gratuita
   - Crie um banco de dados com os módulos:
     - ✅ RediSearch
     - ✅ RedisJSON
   - Copie a URL de conexão (formato: `redis://default:senha@host:porta`)

   **Opção B: Redis Local (Avançado)**
   ```bash
   # macOS (com Homebrew)
   brew install redis-stack
   redis-stack-server

   # Linux (Ubuntu/Debian)
   curl -fsSL https://packages.redis.io/gpg | sudo gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg
   echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/redis.list
   sudo apt-get update
   sudo apt-get install redis-stack-server
   redis-stack-server

   # Docker (qualquer sistema)
   docker run -d -p 6379:6379 redis/redis-stack:latest
   ```

### Passo 1: Clonar ou Baixar o Projeto

```bash
# Se você tem o projeto em um repositório Git
git clone <url-do-repositorio>
cd banco-inter-taskbar

# Ou se já está na pasta do projeto
cd /caminho/para/banco-inter-taskbar
```

### Passo 2: Criar Ambiente Virtual Python

```bash
# Criar ambiente virtual
python3 -m venv .venv

# Ativar ambiente virtual
# No macOS/Linux:
source .venv/bin/activate

# No Windows:
.venv\Scripts\activate

# Você deve ver (.venv) no início do prompt
```

### Passo 3: Instalar Dependências

```bash
# Com o ambiente virtual ativado
pip install -r requirements.txt

# Isso vai instalar:
# - fastapi (framework web)
# - uvicorn (servidor ASGI)
# - redis (cliente Redis)
# - redisvl (busca vetorial)
# - sentence-transformers (embeddings)
# - numpy (operações numéricas)
```

**Nota**: Na primeira execução, o modelo de embeddings (~500MB) será baixado automaticamente.

### Passo 4: Configurar Variáveis de Ambiente

```bash
# Criar arquivo .env
touch .env

# Editar o arquivo .env e adicionar:
# Para Redis Cloud:
REDIS_URL=redis://default:SUA_SENHA@seu-host.cloud.redislabs.com:porta

# Para Redis local (sem senha):
REDIS_URL=redis://localhost:6379/0

# Para Redis local com SSL:
REDIS_URL=rediss://default:senha@localhost:6379
```

**⚠️ IMPORTANTE**: Nunca commite o arquivo `.env` com credenciais reais!

### Passo 5: Iniciar o Servidor

```bash
# Opção A: Usando o script run.sh (recomendado)
chmod +x run.sh
./run.sh

# Opção B: Manualmente
source .venv/bin/activate
uvicorn main:app --reload

# Você deve ver:
# INFO:     Uvicorn running on http://127.0.0.1:8000
# INFO:     Application startup complete.
```

### Passo 6: Carregar Dados Iniciais (Seed)

Em outro terminal (ou no navegador):

```bash
# Via curl
curl -X POST http://localhost:8000/seed

# Ou abra no navegador:
# http://localhost:8000/seed
```

Você deve ver uma resposta como:
```json
{
  "status": "success",
  "counts": {
    "routes": 15,
    "skus": 15,
    "products": 10
  },
  "message": "Data seeded successfully"
}
```

### Passo 7: Abrir a Aplicação

Abra seu navegador e acesse:
```
http://localhost:8000
```

Você deve ver a interface de busca do Banco Inter! 🎉


---

## 🧪 Testando a Aplicação

### Teste 1: Busca Básica

Na interface web, digite:
- `pix` → Deve retornar "Pix - Transferir dinheiro na hora"
- `boleto` → Deve retornar "Pagar Boleto"
- `iphone` → Deve retornar produtos iPhone

### Teste 2: Expansão de Sinônimos (Redis FT.SYNUPDATE)

Digite sinônimos configurados:
- `robaro` → Deve retornar "Bloquear Cartão" ✅ (sinônimo)
- `emprest` → Deve retornar "Empréstimo" ✅ (sinônimo)
- `card` → Deve retornar resultados de cartão ✅ (sinônimo)

### Teste 3: Busca Semântica (Embeddings)

Digite variações e contextos:
- `robaro meu cartao` → Deve retornar "Bloquear Cartão" ✅ (typo + contexto)
- `mandar dinheiro` → Deve retornar "Pix" ✅ (variação)
- `quanto gastei` → Deve retornar "Extrato" ✅ (intenção)
- `dinheiro de volta` → Deve retornar "Cashback" ✅ (contexto)

### Teste 4: Testes Automatizados

```bash
# Ativar ambiente virtual
source .venv/bin/activate

# Testar embeddings (similaridade semântica)
python tests/test_embeddings.py

# Testar busca end-to-end
python tests/test_search_e2e.py

# Testar roteamento semântico
python tests/test_semantic_router.py

# Benchmark de performance
python tests/benchmark.py
```

### Teste 5: API Diretamente

```bash
# Buscar por "pix"
curl "http://localhost:8000/search?q=pix"

# Buscar com typo
curl "http://localhost:8000/search?q=robaro%20meu%20cartao"

# Health check
curl "http://localhost:8000/health"
```

---

## 📊 Exemplos de Busca

### Rotas Bancárias

| Query | Resultado Esperado | Tipo de Match |
|-------|-------------------|---------------|
| `pix` | Pix - Transferir dinheiro | Texto exato |
| `boleto` | Pagar Boleto | Texto exato |
| `extrato` | Extrato | Texto exato |
| `robaro` | Bloquear Cartão | **Sinônimo** (FT.SYNUPDATE) |
| `emprest` | Empréstimo | **Sinônimo** (FT.SYNUPDATE) |
| `card` | Cartão Virtual | **Sinônimo** (FT.SYNUPDATE) |
| `mandar dinheiro` | Pix | **Semântico** (embedding) |
| `pagar conta de luz` | Pagar Boleto | **Semântico** (embedding) |
| `quanto gastei` | Extrato | **Semântico** (embedding) |
| `robaro meu cartao` | Bloquear Cartão | **Sinônimo + Semântico** |

### Produtos Marketplace

| Query | Resultado Esperado |
|-------|-------------------|
| `iphone` | iPhone 15 Pro Max |
| `samsung` | Samsung Galaxy S24 |
| `notebook` | Notebook Dell Inspiron |
| `fone bluetooth` | Fone Bluetooth JBL |

### Produtos Bancários

| Query | Resultado Esperado |
|-------|-------------------|
| `investir` | Investimentos |
| `cdb` | CDB Inter |
| `tesouro` | Tesouro Direto |
| `seguro` | Seguros |

---

## 🎨 Estrutura do Projeto

```
banco-inter-taskbar/
├── main.py                 # Backend FastAPI + lógica Redis
├── config.py               # Configurações (Redis URL, etc)
├── requirements.txt        # Dependências Python
├── .env                    # Variáveis de ambiente (não commitar!)
├── run.sh                  # Script para iniciar servidor
│
├── routes.jsonl            # 15 rotas bancárias
├── skus.jsonl              # 15 produtos marketplace
├── products.jsonl          # 10 produtos bancários
│
├── static/                 # Frontend
│   ├── index.html          # Interface web
│   ├── styles.css          # Tema Banco Inter
│   └── app.js              # Lógica de busca + autocomplete
│
└── tests/                  # Testes automatizados
    ├── test_embeddings.py       # Testa similaridade semântica
    ├── test_search_e2e.py       # Testa busca completa
    ├── test_semantic_router.py  # Testa detecção de intenção
    └── benchmark.py             # Testa performance
```

---

## 🔧 Troubleshooting

### Erro: "Connection refused" ao conectar no Redis

**Solução**:
1. Verifique se o Redis está rodando:
   ```bash
   redis-cli ping  # Deve retornar "PONG"
   ```
2. Verifique a URL no arquivo `.env`
3. Se usar Redis Cloud, verifique se a senha está correta

### Erro: "Module not found: redisvl"

**Solução**:
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### Erro: "Index already exists"

**Solução**: Os índices já foram criados. Isso é normal! Apenas continue usando.

### Busca não retorna resultados

**Solução**:
1. Verifique se os dados foram carregados:
   ```bash
   curl -X POST http://localhost:8000/seed
   ```
2. Verifique os logs do servidor

### Performance lenta na primeira busca

**Solução**: É normal! O modelo de embeddings está sendo carregado. As próximas buscas serão rápidas (~40-80ms).

---

## 📈 Performance Esperada

Com Redis Cloud ou local otimizado:

- **Latência média**: 40-80ms (cliente + servidor)
- **P95**: < 100ms
- **P99**: < 150ms
- **Throughput**: > 100 req/s (single instance)

---

## 🎯 Próximos Passos

Depois de rodar a demo, você pode:

1. **Adicionar mais dados**: Edite os arquivos `.jsonl`
2. **Customizar o modelo**: Troque o embedding model em `main.py`
3. **Melhorar o ranking**: Ajuste os pesos de scoring
4. **Adicionar filtros**: Categoria, preço, estoque
5. **Implementar tracking**: Registre cliques e aprenda com usuários

---

## 📝 Licença

MIT License - Projeto demo para Banco Inter

---

## 🤝 Contribuindo

Sugestões e melhorias são bem-vindas! Áreas de interesse:

- Modelos de embedding melhores
- Algoritmos de ranking avançados
- Melhorias de UI/UX
- Otimizações de performance

---

**Desenvolvido com ❤️ usando Redis 8, FastAPI e Vanilla JS**

**Dúvidas?** Abra uma issue ou entre em contato!
