@echo off
title OmniControl - Disable Windows Auto-Start
color 0c
echo =======================================================
echo   OmniControl - Remove Launch from Windows Startup
echo =======================================================
echo.

python -m backend.startup_manager --disable

echo.
echo Done! OmniControl will no longer start automatically on boot.
echo.
pause
