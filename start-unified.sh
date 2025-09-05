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

# Function to check if a port is available
check_port() {
    local port=$1
    local service_name=$2
    local max_attempts=3
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if lsof -ti:$port >/dev/null 2>&1; then
            echo -e "${SYSTEM_PREFIX} Port $port is in use by $service_name. Attempt $attempt/$max_attempts"
            
            # Get process info
            local pid=$(lsof -ti:$port)
            local process_info=$(ps -p $pid -o pid,ppid,command 2>/dev/null | tail -n +2)
            echo -e "${SYSTEM_PREFIX} Process using port $port: $process_info"
            
            # Try to kill the process
            echo -e "${SYSTEM_PREFIX} Attempting to kill process $pid..."
            if kill -9 $pid 2>/dev/null; then
                echo -e "${SYSTEM_PREFIX} Successfully killed process $pid"
                sleep 2
            else
                echo -e "${SYSTEM_PREFIX} Failed to kill process $pid"
            fi
            
            # Check if port is now free
            if ! lsof -ti:$port >/dev/null 2>&1; then
                echo -e "${SYSTEM_PREFIX} Port $port is now available"
                return 0
            fi
            
            attempt=$((attempt + 1))
            sleep 3
        else
            echo -e "${SYSTEM_PREFIX} Port $port is available for $service_name"
            return 0
        fi
    done
    
    echo -e "${SYSTEM_PREFIX} ❌ Failed to free port $port after $max_attempts attempts"
    return 1
}

# Check if required ports are available
echo -e "${SYSTEM_PREFIX} Checking port availability..."
if ! check_port 8000 "Backend"; then
    echo -e "${SYSTEM_PREFIX} ❌ Cannot start backend on port 8000"
    exit 1
fi

if ! check_port 3000 "Frontend"; then
    echo -e "${SYSTEM_PREFIX} ❌ Cannot start frontend on port 3000"
    exit 1
fi

echo -e "${SYSTEM_PREFIX} ✅ All required ports are available"

# Check if PostgreSQL is running
PG_ISREADY="pg_isready"
if ! command -v pg_isready >/dev/null 2>&1; then
    PG_ISREADY="/opt/homebrew/opt/postgresql@16/bin/pg_isready"
    if [ ! -f "$PG_ISREADY" ]; then
        echo -e "${SYSTEM_PREFIX} ❌ pg_isready not found. Please install PostgreSQL or add it to PATH"
        exit 1
    fi
fi

if ! $PG_ISREADY -h localhost -p 5432 >/dev/null 2>&1; then
    echo -e "${SYSTEM_PREFIX} PostgreSQL is not running. Starting it..."
    brew services start postgresql@16
    echo -e "${SYSTEM_PREFIX} Waiting for PostgreSQL to be ready..."
    for i in {1..30}; do
        if $PG_ISREADY -h localhost -p 5432 >/dev/null 2>&1; then
            echo -e "${SYSTEM_PREFIX} PostgreSQL is ready!"
            break
        fi
        if [ $i -eq 30 ]; then
            echo -e "${SYSTEM_PREFIX} ❌ PostgreSQL failed to start after 30 seconds"
            exit 1
        fi
        sleep 1
    done
else
    echo -e "${SYSTEM_PREFIX} PostgreSQL is already running"
fi

# Verify ports are still free before starting services
echo -e "${SYSTEM_PREFIX} Verifying ports are still free..."
if lsof -ti:8000 >/dev/null 2>&1; then
    echo -e "${SYSTEM_PREFIX} ❌ Port 8000 is still in use, cannot start backend"
    exit 1
fi
if lsof -ti:3000 >/dev/null 2>&1; then
    echo -e "${SYSTEM_PREFIX} ❌ Port 3000 is still in use, cannot start frontend"
    exit 1
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
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
        echo -e "${SYSTEM_PREFIX} Backend process $BACKEND_PID stopped"
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
        echo -e "${SYSTEM_PREFIX} Frontend process $FRONTEND_PID stopped"
    fi
    
    # Also kill any processes that might be using our ports
    echo -e "${SYSTEM_PREFIX} Cleaning up any remaining processes on ports 8000 and 3000..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
    
    echo -e "${SYSTEM_PREFIX} Servers stopped."
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Wait for both processes
wait
