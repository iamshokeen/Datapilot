#!/bin/bash
# DataPilot — Stop all services

echo ""
echo "Stopping DataPilot..."

# Kill backend (uvicorn on 8080)
if lsof -ti:8080 > /dev/null 2>&1; then
    kill $(lsof -ti:8080) 2>/dev/null && echo "  Backend stopped." || true
else
    echo "  Backend not running on :8080."
fi

# Kill frontend (Next.js on 3000)
if lsof -ti:3000 > /dev/null 2>&1; then
    kill $(lsof -ti:3000) 2>/dev/null && echo "  Frontend stopped." || true
else
    echo "  Frontend not running on :3000."
fi

# Docker services
docker compose down 2>/dev/null && echo "  Docker services stopped." || echo "  No Docker services running."

echo "Done."
echo ""
