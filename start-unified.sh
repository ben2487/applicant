#!/bin/bash

# WebBot Unified Logging Startup Script
# This script starts both servers and combines all logs with colorized prefixes

# Colors for different log sources
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Log prefixes
BACKEND_PREFIX="${BLUE}[BACKEND]${NC}"
FRONTEND_PREFIX="${GREEN}[FRONTEND]${NC}"
BROWSER_PREFIX="${PURPLE}[BROWSER]${NC}"
SYSTEM_PREFIX="${YELLOW}[SYSTEM]${NC}"

echo -e "${SYSTEM_PREFIX} Starting WebBot with unified logging..."

# Check if PostgreSQL is running
if ! pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
    echo -e "${SYSTEM_PREFIX} PostgreSQL is not running. Starting it..."
    brew services start postgresql@16
    echo -e "${SYSTEM_PREFIX} Waiting for PostgreSQL to be ready..."
    while ! pg_isready -h localhost -p 5432 >/dev/null 2>&1; do
        sleep 1
    done
    echo -e "${SYSTEM_PREFIX} PostgreSQL is ready!"
fi

# Start Flask backend in background
echo -e "${BACKEND_PREFIX} Starting Flask backend on port 8000..."
DATABASE_URL="postgresql://localhost/webbot" poetry run python -c "from src.backend.app import create_app; app = create_app(); app.run(host='0.0.0.0', port=8000, debug=True)" 2>&1 | sed "s/^/${BACKEND_PREFIX} /" &
BACKEND_PID=$!

# Wait for backend to start
echo -e "${SYSTEM_PREFIX} Waiting for backend to start..."
sleep 5

# Check if backend is running
if curl -s http://localhost:8000/health >/dev/null 2>&1; then
    echo -e "${BACKEND_PREFIX} ✅ Backend is running on http://localhost:8000"
else
    echo -e "${BACKEND_PREFIX} ❌ Backend failed to start"
    exit 1
fi

# Start React frontend in background
echo -e "${FRONTEND_PREFIX} Starting React frontend on port 3000..."
cd frontend
npm run dev 2>&1 | sed "s/^/${FRONTEND_PREFIX} /" &
FRONTEND_PID=$!
cd ..

# Wait for frontend to start
echo -e "${SYSTEM_PREFIX} Waiting for frontend to start..."
sleep 8

# Check if frontend is running
if curl -s http://localhost:3000 >/dev/null 2>&1; then
    echo -e "${FRONTEND_PREFIX} ✅ Frontend is running on http://localhost:3000"
else
    echo -e "${FRONTEND_PREFIX} ❌ Frontend failed to start"
    exit 1
fi

echo -e "${SYSTEM_PREFIX} 🎉 WebBot is now running!"
echo -e "${SYSTEM_PREFIX} Frontend: http://localhost:3000"
echo -e "${SYSTEM_PREFIX} Backend API: http://localhost:8000"
echo -e "${SYSTEM_PREFIX} Press Ctrl+C to stop both servers"
echo ""

# Function to handle cleanup
cleanup() {
    echo -e "${SYSTEM_PREFIX} Stopping servers..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo -e "${SYSTEM_PREFIX} Servers stopped."
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Wait for both processes
wait
