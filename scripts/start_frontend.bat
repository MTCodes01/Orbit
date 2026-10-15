@echo off
echo Starting Orbit Frontend PWA...
cd /d "%~dp0..\frontend"
if not exist "node_modules" (
    echo Installing npm dependencies...
    call npm install
)
npm run dev -- --host 0.0.0.0
pause
