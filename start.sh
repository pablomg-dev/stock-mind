#!/bin/bash

# StockMind Startup Script
# Starts the trading agent, FastAPI backend, and React frontend

PROJECT_DIR="/home/pmg/stock-mind"
cd "$PROJECT_DIR" || exit 1

# Ensure Python dependencies are available (system or venv)
export PATH="$HOME/.cargo/bin:$PATH"
# Use venv if available, otherwise system Python
if [ -f ".venv/bin/activate" ]; then
    . .venv/bin/activate
fi

# Function to cleanup background processes on exit
cleanup() {
    echo ""
    echo "Stopping all processes..."
    if [ -n "$AGENT_PID" ]; then
        kill $AGENT_PID 2>/dev/null
        echo "Stopped agent (PID: $AGENT_PID)"
    fi
    if [ -n "$API_PID" ]; then
        kill $API_PID 2>/dev/null
        echo "Stopped FastAPI (PID: $API_PID)"
    fi
    if [ -n "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
        echo "Stopped frontend (PID: $FRONTEND_PID)"
    fi
    exit 0
}

# Trap Ctrl+C and call cleanup
trap cleanup SIGINT SIGTERM

echo "Starting StockMind..."
echo "================================"

# Start Trading Agent (Terminal 1)
echo "Starting Trading Agent..."
PYTHONPATH=. python3 agent/main.py &
AGENT_PID=$!
echo "Agent started (PID: $AGENT_PID)"

# Start FastAPI Backend (Terminal 2)
echo "Starting FastAPI Backend..."
PYTHONPATH=. python3 -m uvicorn api.server:app --reload --host 0.0.0.0 --port 8000 &
API_PID=$!
echo "FastAPI started (PID: $API_PID)"

# Start React Frontend (Terminal 3)
echo "Starting React Frontend..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd "$PROJECT_DIR"
echo "Frontend started (PID: $FRONTEND_PID)"

echo "================================"
echo "All services started!"
echo "  - Agent: PID $AGENT_PID"
echo "  - FastAPI: http://localhost:8000 (PID: $API_PID)"
echo "  - Frontend: http://localhost:5173 (PID: $FRONTEND_PID)"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for all background processes
wait
