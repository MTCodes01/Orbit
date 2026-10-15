@echo off
echo =======================================================
echo  Installing ViGEmBus Virtual Controller Driver
echo =======================================================
echo.
echo Checking for Administrator privileges...
net session >nul 2>&1
if %errorLevel% == 0 (
    echo Administrator permissions confirmed.
) else (
    echo [NOTE] Requesting Administrator Elevation...
    powershell -Command "Start-Process msiexec.exe -ArgumentList '/i \"%~dp0vgamepad\win\vigem\install\x64\ViGEmBusSetup_x64.msi\"' -Verb RunAs"
    exit /b
)

msiexec.exe /i "%~dp0vgamepad\win\vigem\install\x64\ViGEmBusSetup_x64.msi"
echo.
echo Installation wizard launched. Once finished, your phone will act as a genuine Xbox 360 controller!
pause
