@echo off
echo.
echo Stopping DataPilot...

:: Kill processes on port 8080 (backend)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8080" ^| findstr "LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1 && echo   Backend stopped.
)

:: Kill processes on port 3000 (frontend)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3000" ^| findstr "LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1 && echo   Frontend stopped.
)

:: Docker services
docker compose down
echo   Docker services stopped.

echo Done.
echo.
pause
