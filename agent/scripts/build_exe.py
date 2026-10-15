"""
PyInstaller build script for the Orbit Windows agent.

Usage:
    cd agent
    python scripts/build_exe.py

Output: dist/orbit-agent.exe (standalone, no Python required)
"""

import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
AGENT_DIR = SCRIPT_DIR.parent


def build():
    print("Building Orbit Agent executable...")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",                             # No console window (for tray-only mode)
        "--console",                              # Keep console for first-run prompts (override windowed)
        "--name", "orbit-agent",
        "--paths", str(AGENT_DIR),
        "--icon", str(AGENT_DIR / "resources" / "orbit.ico"),
        "--add-data", f"{AGENT_DIR / 'resources'};resources",
        "--hidden-import", "keyring.backends.Windows",
        "--hidden-import", "keyring.backends.fail",
        "--hidden-import", "pynput.keyboard._win32",
        "--hidden-import", "pynput.mouse._win32",
        "--hidden-import", "PIL.ImageDraw",
        "--hidden-import", "PIL.Image",
        "--collect-all", "pystray",
        "--collect-all", "pyautogui",
        "--distpath", str(AGENT_DIR / "dist"),
        "--workpath", str(AGENT_DIR / "build"),
        "--specpath", str(AGENT_DIR),
        str(AGENT_DIR / "orbit_agent" / "__main__.py"),
    ]

    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=str(AGENT_DIR))
    if result.returncode == 0:
        print("\n[OK] Build complete: dist/orbit-agent.exe")
        print("     Standalone executable ready. No Python required.")
    else:
        print(f"\n[ERROR] Build failed (exit code {result.returncode})")
        sys.exit(result.returncode)


if __name__ == "__main__":
    build()
