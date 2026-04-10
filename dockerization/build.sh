#!/bin/bash
# Build and push multi-platform Docker image

set -e

# Configuration
IMAGE_NAME="gacerioni/gabs-redis-taskbar-global-search"
VERSION="v0.0.1-gabs"
PLATFORMS="linux/amd64,linux/arm64"

echo "🐳 Building Docker image: ${IMAGE_NAME}:${VERSION}"
echo "📦 Platforms: ${PLATFORMS}"
echo ""

# Check if builder exists
if ! docker buildx inspect mybuilder &> /dev/null; then
    echo "🔧 Creating buildx builder..."
    docker buildx create --name mybuilder --use
    docker buildx inspect --bootstrap
fi

# Use the builder
docker buildx use mybuilder

# Build and push
echo "🚀 Building and pushing..."
docker buildx build \
    --platform ${PLATFORMS} \
    -f Dockerfile \
    -t ${IMAGE_NAME}:${VERSION} \
    -t ${IMAGE_NAME}:latest \
    --push \
    ..

echo ""
echo "✅ Image built and pushed successfully!"
echo ""
echo "📌 Tags:"
echo "   - ${IMAGE_NAME}:${VERSION}"
echo "   - ${IMAGE_NAME}:latest"
echo ""
echo "🏃 Run with:"
echo "   docker run -d -p 8092:8092 -e REDIS_URL=redis://localhost:6379 ${IMAGE_NAME}:${VERSION}"
echo ""

