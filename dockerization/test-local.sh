#!/bin/bash
# Test local Docker build without pushing

set -e

IMAGE_NAME="redis-global-search-local"
VERSION="test"

echo "🐳 Building local Docker image for testing..."
echo ""

# Build for current platform only (faster)
docker build \
    -f Dockerfile \
    -t ${IMAGE_NAME}:${VERSION} \
    ..

echo ""
echo "✅ Image built successfully!"
echo ""
echo "🏃 Testing with docker-compose:"
echo "   cd dockerization && docker-compose up -d"
echo ""
echo "Or run standalone:"
echo "   docker run -d -p 8092:8092 -e REDIS_URL=redis://host.docker.internal:6379 ${IMAGE_NAME}:${VERSION}"
echo ""

