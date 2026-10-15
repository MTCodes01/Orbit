"""Windows login autostart configuration using the Windows Registry."""

import logging
import os
import sys
from typing import Optional

logger = logging.getLogger("orbit.autostart")

RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_REG_NAME = "OrbitAgent"


def is_autostart_enabled() -> bool:
    """Check if the agent is registered to run on Windows startup."""
    if sys.platform != "win32":
        return False

    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_READ) as key:
            try:
                winreg.QueryValueEx(key, APP_REG_NAME)
                return True
            except FileNotFoundError:
                return False
    except Exception as exc:
        logger.warning("Failed to check Windows autostart: %s", exc)
        return False


def set_autostart(enable: bool, exe_path: Optional[str] = None) -> bool:
    """Enable or disable startup on user login."""
    if sys.platform != "win32":
        logger.info("Autostart is only supported on Windows.")
        return False

    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
            if enable:
                target = exe_path or sys.executable
                # Wrap path in quotes to handle spaces
                cmd = f'"{os.path.abspath(target)}"'
                winreg.SetValueEx(key, APP_REG_NAME, 0, winreg.REG_SZ, cmd)
                logger.info("Enabled autostart for %s", cmd)
                return True
            else:
                try:
                    winreg.DeleteValue(key, APP_REG_NAME)
                    logger.info("Disabled autostart")
                except FileNotFoundError:
                    pass
                return True
    except Exception as exc:
        logger.error("Failed to update Windows autostart: %s", exc)
        return False
