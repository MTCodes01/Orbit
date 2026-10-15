"""
Windows Startup Manager for OmniControl.
Enables or disables auto-launching on Windows boot via HKCU Run registry key.
Does not require administrator privileges.
"""

import sys
import os
import winreg
import logging

logger = logging.getLogger("startup_manager")

REG_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "OmniControl"


def get_launch_command() -> str:
    """Determine the correct command line to start OmniControl silently in tray."""
    if getattr(sys, "frozen", False):
        # Compiled executable
        exe_path = os.path.abspath(sys.executable)
        return f'"{exe_path}" --tray'
    else:
        # Running from python script
        # Check if pythonw exists in python directory for windowless background execution
        py_dir = os.path.dirname(sys.executable)
        pythonw = os.path.join(py_dir, "pythonw.exe")
        python_exe = pythonw if os.path.exists(pythonw) else sys.executable
        
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        run_server = os.path.join(script_dir, "run_server.py")
        return f'"{python_exe}" "{run_server}" --tray'


def is_startup_enabled() -> bool:
    """Check if OmniControl is set to run on Windows startup."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY_PATH, 0, winreg.KEY_READ) as key:
            val, _ = winreg.QueryValueEx(key, APP_NAME)
            return bool(val)
    except FileNotFoundError:
        return False
    except Exception as e:
        logger.error(f"Error checking startup key: {e}")
        return False


def set_startup(enable: bool) -> bool:
    """Enable or disable auto-start on Windows boot."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
            if enable:
                cmd = get_launch_command()
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
                logger.info(f"Startup enabled with command: {cmd}")
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                    logger.info("Startup disabled")
                except FileNotFoundError:
                    pass
        return True
    except Exception as e:
        logger.error(f"Failed to set startup state: {e}")
        return False


def toggle_startup() -> bool:
    """Toggle current startup state and return new state."""
    current = is_startup_enabled()
    new_state = not current
    set_startup(new_state)
    return new_state


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="OmniControl Startup Configuration")
    parser.add_argument("--status", action="store_true", help="Check startup status")
    parser.add_argument("--enable", action="store_true", help="Enable launch on Windows startup")
    parser.add_argument("--disable", action="store_true", help="Disable launch on Windows startup")
    parser.add_argument("--toggle", action="store_true", help="Toggle launch on Windows startup")

    args = parser.parse_args()
    if args.enable:
        set_startup(True)
        print("Startup enabled.")
    elif args.disable:
        set_startup(False)
        print("Startup disabled.")
    elif args.toggle:
        state = toggle_startup()
        print(f"Startup toggled to: {'Enabled' if state else 'Disabled'}")
    else:
        status = is_startup_enabled()
        print(f"Startup status: {'Enabled' if status else 'Disabled'}")
