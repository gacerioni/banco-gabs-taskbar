# 🐳 Docker Deployment - Banco Inter Taskbar Search

Multi-platform Docker image with support for **linux/amd64** and **linux/arm64** (Apple Silicon).

---

## 🚀 Quick Start

### Using Docker Compose (Recommended for local testing)

```bash
cd dockerization
docker-compose up -d
```

Access the app at: `http://localhost:8092`

---

## 📦 Build Multi-Platform Image

### Prerequisites

```bash
# Create buildx builder (one-time setup)
docker buildx create --name mybuilder --use
docker buildx inspect --bootstrap
```

### Build and Push

```bash
# From project root
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -f dockerization/Dockerfile \
  -t gacerioni/gabs-redis-taskbar-global-search:v0.0.1-gabs \
  --push \
  .
```

Replace `gacerioni/gabs-redis-taskbar-global-search:v0.0.1-gabs` with your Docker Hub repository.

---

## 🏃 Run Published Image

### With External Redis (Production)

```bash
docker run -d \
  --name banco-inter-search \
  -p 8092:8092 \
  -e REDIS_URL=redis://your-redis-host:6379 \
  gacerioni/gabs-redis-taskbar-global-search:v0.0.1-gabs
```

### With Docker Compose (Local with Redis included)

```bash
# Download docker-compose.yml from this folder
docker-compose up -d
```

---

## 🔐 Environment Variables

### Required

| Variable | Description | Default |
|----------|-------------|---------|
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379` |

### Optional

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_HOST` | FastAPI host | `0.0.0.0` |
| `APP_PORT` | FastAPI port | `8092` |
| `DEBUG` | Debug mode | `false` |
| `FTS_WEIGHT` | Full-text search weight | `0.7` |
| `VSS_WEIGHT` | Vector search weight | `0.3` |
| `ROUTER_MODEL_NAME` | Intent router model | `paraphrase-multilingual-MiniLM-L12-v2` |
| `SEARCH_MODEL_NAME` | Search embedding model | `Alibaba-NLP/gte-Qwen2-1.5B-instruct` |

---

## 📊 Health Check

```bash
curl http://localhost:8092/health
```

Expected response:
```json
{
  "status": "healthy",
  "redis": "connected",
  "version": "1.0.0"
}
```

---

## 🗄️ Redis Requirements

The app requires **Redis Stack 7.2+** or **Redis 8.4+** with:
- ✅ RediSearch
- ✅ RedisJSON
- ✅ FT.HYBRID support (Redis 8.4+)

### Redis Cloud

```bash
docker run -d \
  --name banco-inter-search \
  -p 8092:8092 \
  -e REDIS_URL=redis://default:your_password@redis-xxxxx.cloud.redislabs.com:19891 \
  gacerioni/gabs-redis-taskbar-global-search:v0.0.1-gabs
```

---

## 🔧 Troubleshooting

### Container won't start

```bash
# Check logs
docker logs banco-inter-search

# Common issues:
# 1. Redis not reachable → check REDIS_URL
# 2. Model download slow → wait for first startup (downloads ~2GB)
# 3. Port already in use → change -p 8092:XXXX
```

### Reset data

```bash
# Stop container
docker-compose down

# Remove volumes
docker volume rm dockerization_redis-data

# Restart
docker-compose up -d
```

---

## 📁 Files in this folder

- `Dockerfile` - Multi-stage build for production
- `docker-compose.yml` - Local development with Redis
- `.dockerignore` - Excludes unnecessary files from image
- `README.md` - This file

---

## 🎯 Production Checklist

- [ ] Use Redis Cloud or managed Redis instance
- [ ] Set `DEBUG=false`
- [ ] Configure proper `CORS_ORIGINS`
- [ ] Set up monitoring/logging
- [ ] Use HTTPS reverse proxy (nginx/Caddy)
- [ ] Limit container resources (`--memory`, `--cpus`)

---

Built with ❤️ using Redis 8.6 FT.HYBRID + RRF

