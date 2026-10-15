@echo off
title OmniControl - Enable Windows Auto-Start
color 0a
echo =======================================================
echo    OmniControl - Register Launch on Windows Startup
echo =======================================================
echo.

python -m backend.startup_manager --enable

echo.
echo Done! OmniControl will now start in the background on boot.
echo.
pause
