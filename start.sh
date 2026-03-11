#!/bin/bash
# DataPilot — One-click dev startup
# Usage: bash start.sh (or double-click in Git Bash)

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo "╔══════════════════════════════════════╗"
echo "║       DataPilot — Starting Up        ║"
echo "╚══════════════════════════════════════╝"
echo ""

# ── 1. Docker ────────────────────────────────────────────────────────────────
if ! docker info > /dev/null 2>&1; then
    echo "[1/4] Starting Docker Desktop..."
    "/c/Program Files/Docker/Docker/Docker Desktop.exe" &
    echo "      Waiting for Docker daemon (30-60s on first start)..."
    until docker info > /dev/null 2>&1; do
        printf "."
        sleep 3
    done
    echo ""
    echo "      Docker is ready."
else
    echo "[1/4] Docker already running."
fi

# ── 2. Postgres + Redis ───────────────────────────────────────────────────────
echo "[2/4] Starting Postgres + Redis..."
cd "$SCRIPT_DIR"
docker compose up -d postgres redis

# Stop stale Docker backend container if running (frees port 8000)
docker stop datapilot-backend-1 2>/dev/null && echo "      Stopped stale Docker backend." || true

# Wait for postgres to be healthy
echo "      Waiting for Postgres..."
until docker compose exec -T postgres pg_isready -U datapilot > /dev/null 2>&1; do
    sleep 1
done
echo "      Postgres ready."

# ── 3. Backend ────────────────────────────────────────────────────────────────
echo "[3/4] Launching backend on :8080..."
BACKEND_CMD="cd '$SCRIPT_DIR/backend' && python -m uvicorn app.main:app --port 8080 --reload; echo ''; read -p 'Backend stopped. Press Enter to close...'"

if command -v wt.exe > /dev/null 2>&1; then
    wt.exe new-tab --title "DataPilot Backend" -- bash --login -c "$BACKEND_CMD"
else
    start "DataPilot Backend" "$(which bash)" --login -c "$BACKEND_CMD"
fi

# Brief pause so backend window opens first
sleep 1

# ── 4. Frontend ───────────────────────────────────────────────────────────────
echo "[4/4] Launching frontend on :3000..."
FRONTEND_CMD="cd '$SCRIPT_DIR/frontend' && npm run dev; echo ''; read -p 'Frontend stopped. Press Enter to close...'"

if command -v wt.exe > /dev/null 2>&1; then
    wt.exe new-tab --title "DataPilot Frontend" -- bash --login -c "$FRONTEND_CMD"
else
    start "DataPilot Frontend" "$(which bash)" --login -c "$FRONTEND_CMD"
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════╗"
echo "║         DataPilot is live!           ║"
echo "║                                      ║"
echo "║  Frontend:  http://localhost:3000    ║"
echo "║  Backend:   http://localhost:8080    ║"
echo "║  API docs:  http://localhost:8080/docs║"
echo "╚══════════════════════════════════════╝"
echo ""
echo "Check the opened terminal windows for logs."
echo "To stop: Ctrl+C in each terminal, then 'docker compose down'"
echo ""
