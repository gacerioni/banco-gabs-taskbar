#!/bin/bash

# Test script to verify seed is working correctly

echo "🧪 Testing Banco Inter Taskbar Search - Seed Verification"
echo "=========================================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if server is running
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${RED}❌ Server is not running!${NC}"
    echo "Start it with: ./run.sh"
    exit 1
fi

echo -e "${GREEN}✅ Server is running${NC}"
echo ""

# Force re-seed
echo -e "${YELLOW}🌱 Re-seeding database...${NC}"
SEED_RESPONSE=$(curl -s -X POST http://localhost:8000/seed)
echo "$SEED_RESPONSE" | python3 -m json.tool
echo ""

# Test 1: Autocomplete
echo -e "${YELLOW}🔍 Test 1: Autocomplete (emprest)${NC}"
curl -s "http://localhost:8000/autocomplete?q=emprest" | python3 -m json.tool
echo ""

# Test 2: Exact match with synonyms
echo -e "${YELLOW}🔍 Test 2: Exact match with synonyms (emprest)${NC}"
curl -s "http://localhost:8000/search?q=emprest&limit=3" | python3 -m json.tool | grep -A 5 "match_type"
echo ""

# Test 3: Synonym expansion (robaro -> bloquear)
echo -e "${YELLOW}🔍 Test 3: Synonym expansion (robaro)${NC}"
curl -s "http://localhost:8000/search?q=robaro&limit=3" | python3 -m json.tool | grep -A 5 "match_type"
echo ""

# Test 4: Prefix matching (iph -> iPhone)
echo -e "${YELLOW}🔍 Test 4: Prefix matching (iph)${NC}"
curl -s "http://localhost:8000/search?q=iph&limit=3" | python3 -m json.tool | grep -A 5 "match_type"
echo ""

# Test 5: Vector search (me robaro)
echo -e "${YELLOW}🔍 Test 5: Vector/Semantic search (me robaro)${NC}"
curl -s "http://localhost:8000/search?q=me+robaro&limit=3" | python3 -m json.tool | grep -A 5 "match_type"
echo ""

echo "=========================================================="
echo -e "${GREEN}✅ All tests completed!${NC}"
echo ""
echo "Now open http://localhost:8000 and try:"
echo "  - 'emprest' (should show exact match with synonyms)"
echo "  - 'robaro' (should show 'Bloquear Cartão' via synonyms)"
echo "  - 'iph' (should show iPhone via prefix)"
echo "  - 'me robaro' (should show 'Bloquear Cartão' via semantic)"

