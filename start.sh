#!/bin/bash

# Boomerang Startup Script

echo "🚀 Starting Boomerang Financial Analytics Platform..."
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "${YELLOW}⚠️  Python3 is not installed. Please install Python 3.8 or higher.${NC}"
    exit 1
fi

# Check if backend directory exists
if [ ! -d "backend" ]; then
    echo "${YELLOW}⚠️  Backend directory not found. Please run this script from the project root.${NC}"
    exit 1
fi

# Start Backend
echo "${BLUE}📡 Starting Backend Server...${NC}"
cd backend

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies if needed
if [ ! -f "venv/.installed" ]; then
    echo "${YELLOW}Installing dependencies...${NC}"
    pip install -r requirements.txt
    touch venv/.installed
fi

# Start backend in background
echo "${GREEN}✓ Starting FastAPI server on http://localhost:8000${NC}"
uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

cd ..

# Wait for backend to start
sleep 3

# Start Frontend
echo ""
echo "${BLUE}🌐 Starting Frontend Server...${NC}"
cd frontend

# Start frontend server
echo "${GREEN}✓ Starting frontend on http://localhost:8080${NC}"
python3 -m http.server 8080 &
FRONTEND_PID=$!

cd ..

echo ""
echo "${GREEN}========================================${NC}"
echo "${GREEN}✓ Boomerang is now running!${NC}"
echo "${GREEN}========================================${NC}"
echo ""
echo "📊 Frontend:  ${BLUE}http://localhost:8080${NC}"
echo "📡 Backend:   ${BLUE}http://localhost:8000${NC}"
echo "📚 API Docs:  ${BLUE}http://localhost:8000/docs${NC}"
echo ""
echo "${YELLOW}Press Ctrl+C to stop all servers${NC}"
echo ""

# Wait for Ctrl+C
trap "echo '\n${YELLOW}Stopping servers...${NC}'; kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
