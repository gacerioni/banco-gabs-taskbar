# Multi-platform friendly (linux/amd64, linux/arm64): build with buildx, e.g.
#   docker buildx build --platform linux/amd64,linux/arm64 -f Dockerfile \
#     -t gacerioni/gabs-global-search-concierge-redis:v0.0.1 --push .

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Build deps for some wheels; sentence-transformers / torch use prebuilt wheels on amd64/arm64
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# First boot can be slow (model downloads on startup); adjust if needed
HEALTHCHECK --interval=30s --timeout=10s --start-period=180s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=8)"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
