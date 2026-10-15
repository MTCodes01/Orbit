@echo off
echo Starting Orbit Windows Agent...
cd /d "%~dp0..\agent"
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)
call .venv\Scripts\activate
pip install -r requirements.txt -q
python -m orbit_agent
pause
