#!/usr/bin/env bash
# Build & push from repo root (works no matter where you invoke this script from).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

IMAGE_NAME="${IMAGE_NAME:-gacerioni/gabs-global-search-concierge-redis}"
VERSION="${VERSION:-v0.0.42-gabs}"
PLATFORMS="${PLATFORMS:-linux/amd64,linux/arm64}"
BUILDER="${BUILDER:-}"

echo "Building ${IMAGE_NAME}:${VERSION} (context: ${ROOT})"
echo "Platforms: ${PLATFORMS}"
if [[ -n "$BUILDER" ]]; then
  echo "Builder: ${BUILDER}"
  docker buildx use "$BUILDER"
fi

docker buildx build \
  --platform "$PLATFORMS" \
  -f Dockerfile \
  -t "${IMAGE_NAME}:${VERSION}" \
  -t "${IMAGE_NAME}:latest" \
  --push \
  .

echo "Done. Pushed ${IMAGE_NAME}:${VERSION} and ${IMAGE_NAME}:latest"
