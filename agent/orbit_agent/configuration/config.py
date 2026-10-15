r"""
Agent configuration — stored in a JSON file in the user's AppData directory.

On Windows: %APPDATA%\OrbitAgent\config.json
Credentials (device_secret) are stored via the Windows Credential Manager
using the keyring library. The config file never contains plaintext secrets.
"""

from __future__ import annotations

import json
import logging
import os
import platform
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional

import keyring

logger = logging.getLogger("orbit.config")

KEYRING_SERVICE = "OrbitAgent"
KEYRING_SECRET_KEY = "device_secret"
APP_NAME = "OrbitAgent"


def _config_dir() -> Path:
    if platform.system() == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif platform.system() == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / APP_NAME


@dataclass
class AgentConfig:
    backend_url: str = ""
    device_id: Optional[str] = None
    device_name: str = ""

    # Paths (not serialised — derived)
    _config_path: Path = field(default=None, init=False, repr=False)  # type: ignore

    @classmethod
    def load(cls) -> "AgentConfig":
        config_path = _config_dir() / "config.json"
        obj = cls()
        obj._config_path = config_path

        if config_path.exists():
            try:
                data = json.loads(config_path.read_text(encoding="utf-8"))
                obj.backend_url = data.get("backend_url", "")
                obj.device_id = data.get("device_id")
                obj.device_name = data.get("device_name", "")
                logger.debug("Config loaded from %s", config_path)
            except Exception as exc:
                logger.warning("Failed to load config: %s", exc)
        else:
            logger.info("No config found at %s — starting fresh.", config_path)

        return obj

    def save(self):
        path = self._config_path or (_config_dir() / "config.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "backend_url": self.backend_url,
            "device_id": self.device_id,
            "device_name": self.device_name,
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.debug("Config saved to %s", path)

    @property
    def is_paired(self) -> bool:
        return bool(self.device_id)

    # ------------------------------------------------------------------
    # Credential storage (Windows Credential Manager)
    # ------------------------------------------------------------------

    def store_secret(self, secret: str):
        """Store device_secret in OS keyring — never in config.json."""
        keyring.set_password(KEYRING_SERVICE, self.device_id or "unknown", secret)
        logger.debug("Device secret stored in keyring.")

    def retrieve_secret(self) -> Optional[str]:
        if not self.device_id:
            return None
        return keyring.get_password(KEYRING_SERVICE, self.device_id)

    def delete_secret(self):
        if self.device_id:
            try:
                keyring.delete_password(KEYRING_SERVICE, self.device_id)
            except Exception:
                pass

    def clear_pairing(self):
        """Remove all pairing credentials for a fresh start."""
        self.delete_secret()
        self.device_id = None
        self.save()
