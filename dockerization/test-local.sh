#!/usr/bin/env bash
# Local image build (no push) — same context rules as build.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

IMAGE_NAME="${IMAGE_NAME:-redis-global-search-local}"
VERSION="${VERSION:-test}"

echo "Building ${IMAGE_NAME}:${VERSION} from ${ROOT}..."
docker build -f Dockerfile -t "${IMAGE_NAME}:${VERSION}" .

echo ""
echo "Run stack: docker compose up -d"
echo "Or: docker run -d -p 8000:8000 -e REDIS_URL=redis://... ${IMAGE_NAME}:${VERSION}"
