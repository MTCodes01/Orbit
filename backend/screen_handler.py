"""
Screen Capture and Streaming Engine for OmniControl.
Provides low-latency screen frame capture, multi-monitor selection,
accurate coordinate bounding, and touch mapping.
"""

import sys
import os
import time
import ctypes
from typing import Optional, List, Dict, Any
import cv2
import numpy as np

try:
    import mss
except ImportError:
    mss = None

from PIL import ImageGrab


class ScreenManager:
    """Manages high-performance desktop screen capture for mobile streaming."""

    def __init__(self):
        self.user32 = ctypes.windll.user32
        self._sct = None
        self._desktop_attached = False
        self.selected_monitor_idx: Optional[int] = None
        self.active_monitor_bounds = {
            "left": 0,
            "top": 0,
            "width": self.user32.GetSystemMetrics(0),
            "height": self.user32.GetSystemMetrics(1),
            "index": 1,
        }
        self._ensure_thread_desktop()

    def _ensure_thread_desktop(self) -> bool:
        """Attach current thread to interactive desktop for background capture."""
        try:
            hdesk = self.user32.OpenInputDesktop(0, False, 0x01FF)
            if hdesk:
                res = self.user32.SetThreadDesktop(hdesk)
                if res:
                    self._desktop_attached = True
                    return True
        except Exception:
            pass
        return False

    def _get_mss(self):
        if self._sct is None and mss is not None:
            try:
                self._ensure_thread_desktop()
                self._sct = mss.MSS()
            except Exception:
                self._sct = None
        return self._sct

    def get_monitors_list(self) -> List[Dict[str, Any]]:
        """
        List all connected displays with their geometry and primary status.
        Index 0 is the combined virtual desktop (all screens).
        Index 1..N are individual physical displays.
        """
        sct = self._get_mss()
        if not sct or not sct.monitors:
            w = self.user32.GetSystemMetrics(0)
            h = self.user32.GetSystemMetrics(1)
            return [{
                "id": 1,
                "name": "Main Display",
                "width": w,
                "height": h,
                "left": 0,
                "top": 0,
                "is_primary": True
            }]

        monitors = []
        for i, m in enumerate(sct.monitors):
            is_primary = bool(m.get("is_primary", False) or (m["left"] == 0 and m["top"] == 0 and i > 0))
            if i == 0:
                name = f"All Displays ({m['width']}x{m['height']})"
            elif is_primary:
                name = f"Display {i} (Primary - {m['width']}x{m['height']})"
            else:
                name = f"Display {i} ({m['width']}x{m['height']})"

            monitors.append({
                "id": i,
                "name": name,
                "width": m["width"],
                "height": m["height"],
                "left": m["left"],
                "top": m["top"],
                "is_primary": is_primary
            })

        return monitors

    def get_primary_monitor_index(self) -> int:
        """Find the 1-based index of the Primary display in MSS monitors list."""
        sct = self._get_mss()
        if not sct or len(sct.monitors) < 2:
            return 1

        # Check for explicit is_primary or (left == 0 and top == 0)
        for i in range(1, len(sct.monitors)):
            m = sct.monitors[i]
            if m.get("is_primary") is True:
                return i
            if m["left"] == 0 and m["top"] == 0:
                return i

        return 1

    def set_active_monitor(self, monitor_idx: int):
        """Set the active monitor to capture."""
        sct = self._get_mss()
        if sct and 0 <= monitor_idx < len(sct.monitors):
            self.selected_monitor_idx = monitor_idx
            m = sct.monitors[monitor_idx]
            self.active_monitor_bounds = {
                "left": m["left"],
                "top": m["top"],
                "width": m["width"],
                "height": m["height"],
                "index": monitor_idx
            }

    def capture_frame(self, scale: float = 0.75, quality: int = 55, monitor_idx: Optional[int] = None) -> Optional[bytes]:
        """
        Capture the requested display, scale it down, and encode to compressed JPEG.
        Defaults to the Primary display.
        """
        sct = self._get_mss()
        frame = None
        current_m = None

        if sct is not None and sct.monitors:
            # Determine monitor index
            if monitor_idx is not None and 0 <= monitor_idx < len(sct.monitors):
                target_idx = monitor_idx
            elif self.selected_monitor_idx is not None and 0 <= self.selected_monitor_idx < len(sct.monitors):
                target_idx = self.selected_monitor_idx
            else:
                target_idx = self.get_primary_monitor_index()

            self.selected_monitor_idx = target_idx
            current_m = sct.monitors[target_idx]
            self.active_monitor_bounds = {
                "left": current_m["left"],
                "top": current_m["top"],
                "width": current_m["width"],
                "height": current_m["height"],
                "index": target_idx
            }

            try:
                shot = sct.grab(current_m)
                frame = np.array(shot)  # BGRA
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            except Exception:
                # Retry attaching thread desktop
                self._ensure_thread_desktop()
                try:
                    self._sct = mss.MSS()
                    current_m = self._sct.monitors[target_idx]
                    shot = self._sct.grab(current_m)
                    frame = np.array(shot)
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                except Exception:
                    frame = None

        # Fallback to PIL ImageGrab if MSS fails
        if frame is None:
            try:
                pil_img = ImageGrab.grab(all_screens=True if monitor_idx == 0 else False)
                rgb = np.array(pil_img)
                frame = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
                self.active_monitor_bounds = {
                    "left": 0,
                    "top": 0,
                    "width": frame.shape[1],
                    "height": frame.shape[0],
                    "index": 1
                }
            except Exception:
                return None

        # Scaling based on the captured monitor's actual dimensions
        src_w = frame.shape[1]
        src_h = frame.shape[0]

        scale = max(0.25, min(scale, 1.0))
        if scale < 0.98:
            target_w = int(src_w * scale)
            target_h = int(src_h * scale)
            frame = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_LINEAR)

        # JPEG Compression
        quality = max(20, min(quality, 95))
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        success, encoded_img = cv2.imencode('.jpg', frame, encode_param)

        if success:
            return encoded_img.tobytes()
        return None


# Global Screen Manager instance
screen_manager = ScreenManager()
