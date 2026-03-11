@echo off
setlocal

echo.
echo  ==========================================
echo        DataPilot -- Starting Up
echo  ==========================================
echo.

:: ── 1. Docker ────────────────────────────────────────────────────────────────
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [1/4] Starting Docker Desktop...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    echo       Waiting for Docker daemon (30-60s on first start)...
    :waitdocker
    timeout /t 3 /nobreak >nul
    docker info >nul 2>&1
    if %errorlevel% neq 0 goto waitdocker
    echo       Docker is ready.
) else (
    echo [1/4] Docker already running.
)

:: ── 2. Postgres + Redis ───────────────────────────────────────────────────────
echo [2/4] Starting Postgres + Redis...
docker compose up -d postgres redis

:: Stop stale backend container if running
docker stop datapilot-backend-1 >nul 2>&1

:: Wait for postgres
echo       Waiting for Postgres...
:waitpg
timeout /t 2 /nobreak >nul
docker compose exec -T postgres pg_isready -U datapilot >nul 2>&1
if %errorlevel% neq 0 goto waitpg
echo       Postgres ready.

:: ── 3. Backend ────────────────────────────────────────────────────────────────
echo [3/4] Launching backend on :8080...
start "DataPilot Backend" cmd /k "cd /d "%~dp0backend" && python -m uvicorn app.main:app --port 8080 --reload"

timeout /t 2 /nobreak >nul

:: ── 4. Frontend ───────────────────────────────────────────────────────────────
echo [4/4] Launching frontend on :3000...
start "DataPilot Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

:: ── Done ──────────────────────────────────────────────────────────────────────
echo.
echo  ==========================================
echo        DataPilot is live!
echo.
echo    Frontend:  http://localhost:3000
echo    Backend:   http://localhost:8080
echo    API docs:  http://localhost:8080/docs
echo  ==========================================
echo.
echo  Check the opened terminal windows for logs.
echo  To stop: close the terminal windows, then run stop.bat
echo.
pause
