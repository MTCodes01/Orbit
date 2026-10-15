"""
System tray icon for the Orbit agent (Windows).
Uses pystray + Pillow.

Shows connection status and provides:
- Open settings (prints config path)
- Reconnect
- Disconnect
- Exit
"""

from __future__ import annotations

import logging
import threading
from typing import Optional

logger = logging.getLogger("orbit.tray")


def _make_icon_image(color: str = "#6366f1") -> "Image":
    """Generate a simple circle icon with the given color."""
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([8, 8, 56, 56], fill=color)
    # Small orbit ring
    draw.arc([4, 4, 60, 60], 0, 360, fill="white", width=3)
    return img


class TrayIcon:
    def __init__(self, client):
        self.client = client
        self._icon = None
        self._thread: Optional[threading.Thread] = None
        client.on_status_change = self._on_status

    def _on_status(self, status: str):
        if self._icon:
            self._icon.title = f"Orbit Agent — {status}"
            color = (
                "#22c55e" if status == "connected"
                else "#f59e0b" if "reconnecting" in status or status in ("connecting", "authenticating", "registering")
                else "#ef4444"
            )
            try:
                self._icon.icon = _make_icon_image(color)
            except Exception:
                pass

    def start_in_thread(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        try:
            import pystray
            from pystray import MenuItem, Menu
            from orbit_agent.configuration.autostart import is_autostart_enabled, set_autostart

            icon_img = _make_icon_image("#f59e0b")  # Starting = amber

            menu = Menu(
                MenuItem("Orbit Agent", None, enabled=False),
                Menu.SEPARATOR,
                MenuItem("Start with Windows", self._toggle_autostart, checked=lambda item: is_autostart_enabled()),
                MenuItem("Show Config & Logs", self._show_config),
                MenuItem("Reconnect", self._reconnect),
                MenuItem("Disconnect", self._disconnect),
                Menu.SEPARATOR,
                MenuItem("Exit", self._exit),
            )

            self._icon = pystray.Icon(
                "OrbitAgent",
                icon=icon_img,
                title="Orbit Agent — starting",
                menu=menu,
            )
            self._icon.run()
        except ImportError:
            logger.info("pystray not available — running without tray icon.")
        except Exception as exc:
            logger.warning("Tray icon error: %s", exc)

    def _toggle_autostart(self, icon, item):
        from orbit_agent.configuration.autostart import is_autostart_enabled, set_autostart
        current = is_autostart_enabled()
        set_autostart(not current)

    def _show_config(self, icon, item):
        from orbit_agent.configuration.config import _config_dir
        from orbit_agent.diagnostics.logger import _log_dir
        logger.info("Config dir: %s, Log dir: %s", _config_dir(), _log_dir())
        print(f"Config: {_config_dir()}\nLogs: {_log_dir()}")

    def _reconnect(self, icon, item):
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            loop.call_soon_threadsafe(asyncio.create_task, self.client._connect_and_run())
        except Exception as exc:
            logger.warning("Reconnect from tray failed: %s", exc)

    def _disconnect(self, icon, item):
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            loop.call_soon_threadsafe(asyncio.create_task, self.client.stop())
        except Exception as exc:
            logger.warning("Disconnect from tray failed: %s", exc)

    def _exit(self, icon, item):
        import asyncio
        import sys
        icon.stop()
        try:
            loop = asyncio.get_event_loop()
            loop.call_soon_threadsafe(asyncio.create_task, self.client.stop())
        except Exception:
            pass
        sys.exit(0)

    def stop(self):
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass
