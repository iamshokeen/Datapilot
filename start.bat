@echo off
setlocal EnableDelayedExpansion

echo.
echo  =========================================
echo        DataPilot -- Starting Up
echo  =========================================
echo.

set "ROOT=%~dp0"
set "BACKEND_DIR=%ROOT%backend"
set "FRONTEND_DIR=%ROOT%frontend"

:: ── 1. Docker ─────────────────────────────────────────────────────────────────
docker info >nul 2>&1
if !errorlevel! neq 0 (
    echo [1/4] Starting Docker Desktop...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
) else (
    echo [1/4] Docker already running.
)

:wait_docker
docker info >nul 2>&1
if !errorlevel! neq 0 (
    echo       Waiting for Docker daemon...
    timeout /t 3 /nobreak >nul
    goto wait_docker
)
echo       Docker ready.

:: ── 2. Postgres + Redis ───────────────────────────────────────────────────────
echo [2/4] Starting Postgres + Redis...
docker compose up -d postgres redis
docker stop datapilot-backend-1 >nul 2>&1

:wait_pg
docker compose exec -T postgres pg_isready -U datapilot >nul 2>&1
if !errorlevel! neq 0 (
    timeout /t 2 /nobreak >nul
    goto wait_pg
)
echo       Postgres ready.

:: ── 3. Backend ────────────────────────────────────────────────────────────────
echo [3/4] Launching backend on :8080...
start "DataPilot Backend" cmd /k cd /d "%BACKEND_DIR%" ^&^& python -m uvicorn app.main:app --port 8080 --reload

timeout /t 2 /nobreak >nul

:: ── 4. Frontend ───────────────────────────────────────────────────────────────
echo [4/4] Launching frontend on :3000...
start "DataPilot Frontend" cmd /k cd /d "%FRONTEND_DIR%" ^&^& npm run dev

:: ── Done ──────────────────────────────────────────────────────────────────────
echo.
echo  =========================================
echo        DataPilot is live!
echo.
echo    Frontend:  http://localhost:3000
echo    Backend:   http://localhost:8080
echo    API docs:  http://localhost:8080/docs
echo  =========================================
echo.
echo  Check the opened terminal windows for logs.
pause
