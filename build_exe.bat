@echo off
title OmniControl - Windows .EXE Compiler
color 0b
echo =======================================================
echo    OmniControl - Windows Executable (.exe) Compiler
echo =======================================================
echo.
echo Compiling OmniControl into a standalone Windows .exe...
echo.

python build_exe.py

if %ERRORLEVEL% equ 0 (
    echo.
    echo =======================================================
    echo  SUCCESS: Output located in 'dist\OmniControl.exe'
    echo =======================================================
    echo.
) else (
    echo.
    echo =======================================================
    echo  ERROR: Build failed with code %ERRORLEVEL%.
    echo =======================================================
    echo.
)

pause
