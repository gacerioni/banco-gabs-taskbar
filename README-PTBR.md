# 🔍 Redis Global Search — Taskbar Demo

**Customer 360 Global Search Demo** - Busca híbrida super rápida (texto + semântica) para rotas bancárias, produtos de marketplace e serviços financeiros.

Construído com **Redis 8 + RediSearch + RedisVL** para performance de sub-segundos.

> 🇺🇸 **[Read the English guide](README.md)**

---

## 🎯 Funcionalidades

- **🔍 Busca Híbrida**: Texto (exato + sinônimos) + Vetor (semântica)
- **📚 Expansão de Sinônimos**: Expande automaticamente via `FT.SYNUPDATE`
- **🧠 Compreensão Semântica**: Lida com erros de digitação e variações através de embeddings (`robaro meu cartao` → "Bloquear Cartão")
- **🎯 Detecção de Intenção**: Detecta automaticamente a intenção do usuário
- **⚡ Performance Altíssima**: Latência média de ~40-80ms
- **⌨️ Autocomplete em Tempo Real**: Sugestões instantâneas usando `FT.SUGGET`
- **⚙️ Painel Admin e Hot Reload**: Indexe novas SKUs instantaneamente com geração automática de autocomplete.

---

## 🚀 Como iniciar rápido com Docker Compose

É muito simples subir o ambiente de demonstração usando o Docker Compose.

### 1. Pré-requisitos
- **Docker** e **Docker Compose** instalados
- **Banco de Dados Redis 8+** (Crie gratuitamente em [Redis Cloud](https://redis.com/try-free/))

### 2. Configure o Ambiente
Crie um arquivo `.env` na raiz do projeto com sua string de conexão:
```bash
# Redis Cloud (recomendado)
REDIS_URL=redis://default:sua-senha@redis-xxxxx.cloud.redislabs.com:xxxxx

# Ou Redis Local
REDIS_URL=redis://localhost:6379/0
```

### 3. Suba o Container
```bash
docker-compose up -d --build
```
Isso fará o build da API em Python e iniciará o servidor web na porta 8000.

### 4. Auto-Seed (População Automática)
Quando a API inicia, ela detecta automaticamente se os índices do RediSearch existem no seu banco. Caso não existam, o processo de "seed" rodará automaticamente em background (cria os índices, gera embeddings vetoriais, configura o autocomplete e salva os dados).

*(Nota: Se algum dia precisar re-popular ou resetar o banco de dados manualmente, basta rodar `curl -X POST http://localhost:8000/seed`)*

### 5. Acesse a Demonstração
Abra **http://localhost:8000** no seu navegador.

Tente buscar por:
- `robaro meu cartao` (com erro de digitação) → encontra "Bloquear Cartão"
- `mandar dinheiro` → encontra "Pix"
- `iphone` → encontra "iPhone 15 Pro Max"

Acesse também **http://localhost:8000/admin** para ver o Painel Administrativo, adicionar novos itens e testar a atualização em tempo real (Hot Reload)!

---

## 💻 Instalação Manual (Sem Docker)

Se preferir rodar sem o Docker:

```bash
# 1. Crie o ambiente virtual e instale dependências
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Crie o arquivo .env com o REDIS_URL

# 3. Inicie o servidor (o banco será populado automaticamente no primeiro uso!)
./run.sh
```

Aproveite para explorar todo o poder do Redis 8 Search & Query!
