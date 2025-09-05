#!/bin/bash

# WebBot Server Startup Script
# This script starts both the Flask backend and React frontend

# Check if verbose mode is enabled
VERBOSE=${VERBOSE:-0}
if [ "$VERBOSE" = "1" ]; then
    echo "🔍 Verbose logging enabled"
    set -x  # Print commands as they execute
fi

echo "Starting WebBot servers..."

# Check network connectivity
echo "Checking network connectivity..."
if scutil --nwi | grep -q "Reachable"; then
    echo "✅ Network is connected"
else
    echo "❌ No network connection detected. Please check your WiFi connection."
    echo "Network status:"
    scutil --nwi
    exit 1
fi

# Check if PostgreSQL is running
if ! pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
    echo "PostgreSQL is not running. Starting it..."
    make db-up
    echo "Waiting for PostgreSQL to be ready..."
    make db-wait
fi

# Start Flask backend
echo "Starting Flask backend on port 8000..."
if [ "$VERBOSE" = "1" ]; then
    echo "🔍 Starting Flask with verbose logging..."
    DATABASE_URL="postgresql://localhost/webbot" poetry run python -c "from src.backend.app import create_app; app = create_app(); app.run(host='0.0.0.0', port=8000, debug=True)" &
else
    DATABASE_URL="postgresql://localhost/webbot" poetry run python -c "from src.backend.app import create_app; app = create_app(); app.run(host='0.0.0.0', port=8000, debug=False)" > flask.log 2>&1 &
fi
BACKEND_PID=$!

# Wait for backend to start
echo "Waiting for backend to start..."
sleep 3

# Check if backend is running
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Backend is running on http://localhost:8000"
else
    echo "❌ Backend failed to start. Check flask.log for details."
    exit 1
fi

# Start React frontend
echo "Starting React frontend on port 3000..."
cd frontend
if [ "$VERBOSE" = "1" ]; then
    echo "🔍 Starting React with verbose logging..."
    npm run dev &
else
    npm run dev > ../frontend.log 2>&1 &
fi
FRONTEND_PID=$!
cd ..

# Wait for frontend to start
echo "Waiting for frontend to start..."
sleep 5

# Check if frontend is running
if curl -s http://localhost:3000 > /dev/null; then
    echo "✅ Frontend is running on http://localhost:3000"
else
    echo "❌ Frontend failed to start. Check frontend.log for details."
    exit 1
fi

echo ""
echo "🎉 WebBot is now running!"
echo "Frontend: http://localhost:3000"
echo "Backend API: http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop both servers"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Stopping servers..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo "Servers stopped."
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Wait for user to stop
wait
