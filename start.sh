#!/bin/bash
# FuzzyEval — start both backend and frontend

echo "🔍 Starting FuzzyEval..."
echo ""

# Start backend
echo "🐍 Starting FastAPI backend on :8000..."
cd "$(dirname "$0")/backend"
uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Start frontend
echo "⚛️  Starting React frontend on :5173..."
cd "$(dirname "$0")/frontend"
npx vite --host &
FRONTEND_PID=$!

echo ""
echo "✅ FuzzyEval running!"
echo "   Frontend: http://localhost:5173"
echo "   Backend:  http://localhost:8000"
echo "   API docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
