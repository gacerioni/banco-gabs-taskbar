#!/bin/bash
# Fresh Start Script
# Flushes Redis and starts server with fresh data

set -e  # Exit on error

echo "🧹 FRESH START SCRIPT"
echo "=================================================================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Redis is running
echo "🔍 Checking Redis connection..."
if ! redis-cli ping > /dev/null 2>&1; then
    echo -e "${RED}❌ Redis is not running!${NC}"
    echo "   Start Redis first: redis-server"
    exit 1
fi
echo -e "${GREEN}✅ Redis is running${NC}"
echo ""

# Ask for confirmation
echo -e "${YELLOW}⚠️  WARNING: This will DELETE ALL DATA in Redis!${NC}"
read -p "Continue? (y/N): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

# Flush Redis
echo ""
echo "🗑️  Flushing Redis database..."
redis-cli FLUSHDB
echo -e "${GREEN}✅ Redis flushed${NC}"
echo ""

# Start server
echo "🚀 Starting server..."
echo "=================================================================================="
echo ""
./run.sh

