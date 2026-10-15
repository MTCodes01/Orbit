@echo off
echo Building Orbit Agent Standalone Windows Executable (.exe)...
cd /d "%~dp0..\agent"
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)
call .venv\Scripts\activate
pip install -r requirements.txt -q
python scripts/build_exe.py
pause
