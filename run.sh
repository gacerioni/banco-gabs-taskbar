#!/bin/bash

# Redis Global Search Taskbar - Startup Script
# This script starts the FastAPI server (Redis Cloud configured in main.py)

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 Redis Global Search Taskbar - Starting...${NC}\n"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo -e "${RED}❌ Virtual environment not found!${NC}"
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv .venv
    source .venv/bin/activate
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi

# Start FastAPI server
echo -e "${YELLOW}🚀 Starting FastAPI server...${NC}"
echo -e "${GREEN}✅ Server will be available at: ${BLUE}http://localhost:8000${NC}\n"
echo -e "${YELLOW}📡 Using Redis Cloud (configured in main.py)${NC}"
echo -e "${YELLOW}Press CTRL+C to stop the server${NC}\n"

# Start uvicorn
uvicorn main:app --reload

