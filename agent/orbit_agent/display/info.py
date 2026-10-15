"""
Display information — primary and secondary monitors.

Uses win32api on Windows for multi-monitor support.
Falls back to pyautogui.size() for basic single-monitor info.
"""

from __future__ import annotations

import logging
import platform
from dataclasses import dataclass, field
from typing import List

logger = logging.getLogger("orbit.display")


@dataclass
class MonitorInfo:
    index: int
    width: int
    height: int
    x: int
    y: int
    is_primary: bool
    dpi: float = 96.0


@dataclass
class DisplayInfo:
    primary_width: int
    primary_height: int
    monitors: List[MonitorInfo] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "primary_width": self.primary_width,
            "primary_height": self.primary_height,
            "monitor_count": len(self.monitors),
            "monitors": [
                {
                    "index": m.index,
                    "width": m.width,
                    "height": m.height,
                    "x": m.x,
                    "y": m.y,
                    "is_primary": m.is_primary,
                    "dpi": m.dpi,
                }
                for m in self.monitors
            ],
        }


def get_display_info() -> DisplayInfo:
    """Query actual monitor information. Windows multi-monitor aware."""
    if platform.system() == "Windows":
        return _get_windows_display_info()
    return _get_fallback_display_info()


def _get_windows_display_info() -> DisplayInfo:
    try:
        import win32api
        monitors = win32api.EnumDisplayMonitors()
        monitor_list = []
        primary_w, primary_h = 1920, 1080

        for idx, (hmon, _, rect) in enumerate(monitors):
            x, y, x2, y2 = rect
            w, h = x2 - x, y2 - y
            info = win32api.GetMonitorInfo(hmon)
            is_primary = bool(info.get("Flags", 0) & 1)
            mon = MonitorInfo(
                index=idx,
                width=w,
                height=h,
                x=x,
                y=y,
                is_primary=is_primary,
            )
            monitor_list.append(mon)
            if is_primary:
                primary_w, primary_h = w, h

        if not monitor_list:
            return _get_fallback_display_info()

        return DisplayInfo(
            primary_width=primary_w,
            primary_height=primary_h,
            monitors=monitor_list,
        )
    except Exception as exc:
        logger.warning("win32api display query failed: %s", exc)
        return _get_fallback_display_info()


def _get_fallback_display_info() -> DisplayInfo:
    try:
        import pyautogui
        w, h = pyautogui.size()
    except Exception:
        w, h = 1920, 1080

    mon = MonitorInfo(index=0, width=w, height=h, x=0, y=0, is_primary=True)
    return DisplayInfo(primary_width=w, primary_height=h, monitors=[mon])
