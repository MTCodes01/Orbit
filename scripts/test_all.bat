@echo off
echo Running All Orbit Tests...

echo.
echo ===================================
echo [1/3] Backend Tests
echo ===================================
cd /d "%~dp0..\backend"
set PYTHONPATH=%~dp0..;%~dp0..\backend
call .venv\Scripts\pytest.exe -v
if errorlevel 1 (
    echo Backend tests failed!
    pause
    exit /b %errorlevel%
)

echo.
echo ===================================
echo [2/3] Agent Tests
echo ===================================
cd /d "%~dp0..\agent"
set PYTHONPATH=%~dp0..;%~dp0..\agent
call ..\backend\.venv\Scripts\pytest.exe -v
if errorlevel 1 (
    echo Agent tests failed!
    pause
    exit /b %errorlevel%
)

echo.
echo ===================================
echo [3/3] Frontend Tests
echo ===================================
cd /d "%~dp0..\frontend"
call npm test
if errorlevel 1 (
    echo Frontend tests failed!
    pause
    exit /b %errorlevel%
)

echo.
echo ===================================
echo All tests passed successfully!
echo ===================================
pause
