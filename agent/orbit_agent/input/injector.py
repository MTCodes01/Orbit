"""
Windows input injector using pyautogui + pynput.

Design decisions:
- pyautogui handles absolute mouse movement and clicking.
- pynput handles keyboard injection (better Unicode support).
- All held-state tracking is explicit; release_all() is called on shutdown/disconnect.
- Screen resolution is queried at startup for relative-to-absolute conversion.

Platform limitation note:
  pyautogui and pynput cannot inject input into applications running with
  elevated privileges (UAC dialogs, Task Manager in some configs) unless the
  agent itself is elevated. Document this limitation; do NOT request elevation
  by default.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, Set

import pyautogui
from pynput.keyboard import Controller as KeyboardController, Key, KeyCode

logger = logging.getLogger("orbit.input")

# Prevent pyautogui from throwing FailSafeException by moving to corner
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0  # We control timing ourselves

# Key mapping from Orbit canonical names → pynput Key / character
SPECIAL_KEY_MAP: Dict[str, Key] = {
    "escape":      Key.esc,
    "enter":       Key.enter,
    "tab":         Key.tab,
    "backspace":   Key.backspace,
    "delete":      Key.delete,
    "insert":      Key.insert,
    "home":        Key.home,
    "end":         Key.end,
    "pageup":      Key.page_up,
    "pagedown":    Key.page_down,
    "arrowup":     Key.up,
    "arrowdown":   Key.down,
    "arrowleft":   Key.left,
    "arrowright":  Key.right,
    "ctrl":        Key.ctrl,
    "shift":       Key.shift,
    "alt":         Key.alt,
    "meta":        Key.cmd,
    "space":       Key.space,
    "printscreen": Key.print_screen,
    "scrolllock":  Key.scroll_lock,
    "pause":       Key.pause,
    "capslock":    Key.caps_lock,
    "numlock":     Key.num_lock,
    # Function keys
    **{f"f{i}": getattr(Key, f"f{i}") for i in range(1, 13)},
}

MOUSE_BUTTON_MAP = {
    "left":   "left",
    "right":  "right",
    "middle": "middle",
}


class InputInjector:
    """Thread-safe input injector for mouse and keyboard events."""

    def __init__(self):
        self._kb = KeyboardController()
        self._held_keys: Set[str] = set()          # Orbit key names currently pressed
        self._held_buttons: Set[str] = set()       # Mouse buttons currently pressed

        # Get screen dimensions for relative → absolute cursor math
        import pyautogui
        self._screen_w, self._screen_h = pyautogui.size()
        logger.info("Screen size: %dx%d", self._screen_w, self._screen_h)

    def _get_virtual_bounds(self) -> tuple[int, int, int, int]:
        """Returns (vx, vy, vw, vh) of the entire virtual desktop spanning all monitors."""
        try:
            import win32api
            # SM_XVIRTUALSCREEN = 76, SM_YVIRTUALSCREEN = 77, SM_CXVIRTUALSCREEN = 78, SM_CYVIRTUALSCREEN = 79
            vx = win32api.GetSystemMetrics(76)
            vy = win32api.GetSystemMetrics(77)
            vw = win32api.GetSystemMetrics(78)
            vh = win32api.GetSystemMetrics(79)
            if vw > 0 and vh > 0:
                return vx, vy, vw, vh
        except Exception:
            pass
        return 0, 0, self._screen_w, self._screen_h

    # ------------------------------------------------------------------
    # Mouse
    # ------------------------------------------------------------------

    def pointer_move(self, dx: float, dy: float):
        """Move cursor by relative delta across all displays using native OS mouse events."""
        try:
            # On Windows, mouse_event with MOUSEEVENTF_MOVE (0x0001) lets the OS
            # natively handle mouse acceleration, multi-monitor topology, and negative coordinates
            import ctypes
            ctypes.windll.user32.mouse_event(0x0001, int(round(dx)), int(round(dy)), 0, 0)
        except Exception:
            try:
                cx, cy = pyautogui.position()
                vx, vy, vw, vh = self._get_virtual_bounds()
                nx = max(vx, min(vx + vw - 1, cx + int(dx)))
                ny = max(vy, min(vy + vh - 1, cy + int(dy)))
                pyautogui.moveTo(nx, ny, _pause=False)
            except Exception as exc:
                logger.debug("pointer_move fallback error: %s", exc)

    def set_cursor_position(self, x: float, y: float):
        """Move cursor to absolute position across multi-monitor virtual desktop."""
        try:
            import ctypes
            ctypes.windll.user32.SetCursorPos(int(round(x)), int(round(y)))
            logger.info("Cursor positioned at (%d, %d)", int(x), int(y))
        except Exception:
            try:
                pyautogui.moveTo(int(x), int(y), _pause=False)
            except Exception as exc:
                logger.warning("set_cursor_position error: %s", exc)

    def jump_to_monitor(self, monitor_index: int, monitors: list):
        """Instantly center cursor in a specific monitor on this device."""
        try:
            for m in monitors:
                idx = getattr(m, 'index', None) if not isinstance(m, dict) else m.get('index')
                if idx == monitor_index:
                    mx = getattr(m, 'x', 0) if not isinstance(m, dict) else m.get('x', 0)
                    my = getattr(m, 'y', 0) if not isinstance(m, dict) else m.get('y', 0)
                    mw = getattr(m, 'width', 1920) if not isinstance(m, dict) else m.get('width', 1920)
                    mh = getattr(m, 'height', 1080) if not isinstance(m, dict) else m.get('height', 1080)
                    target_x = mx + mw // 2
                    target_y = my + mh // 2
                    self.set_cursor_position(target_x, target_y)
                    logger.info("Jumped cursor to monitor %d at (%d, %d)", monitor_index, target_x, target_y)
                    return
        except Exception as exc:
            logger.warning("jump_to_monitor error: %s", exc)

    def mouse_down(self, button: str):
        btn = MOUSE_BUTTON_MAP.get(button, "left")
        try:
            pyautogui.mouseDown(button=btn, _pause=False)
            self._held_buttons.add(button)
            logger.debug("mouse_down: %s", button)
        except Exception as exc:
            logger.warning("mouse_down error: %s", exc)

    def mouse_up(self, button: str):
        btn = MOUSE_BUTTON_MAP.get(button, "left")
        try:
            pyautogui.mouseUp(button=btn, _pause=False)
            self._held_buttons.discard(button)
            logger.debug("mouse_up: %s", button)
        except Exception as exc:
            logger.warning("mouse_up error: %s", exc)

    def scroll(self, dx: float, dy: float):
        """Scroll by delta. Positive dy = scroll down."""
        try:
            # pyautogui scroll: positive = up, negative = down
            clicks = int(-dy / 40)  # ~40px per click
            if clicks != 0:
                pyautogui.scroll(clicks, _pause=False)
            if abs(dx) > 40:
                h_clicks = int(dx / 40)
                pyautogui.hscroll(h_clicks, _pause=False)
        except Exception as exc:
            logger.debug("scroll error: %s", exc)

    # ------------------------------------------------------------------
    # Keyboard
    # ------------------------------------------------------------------

    def key_down(self, key_name: str):
        pynput_key = self._resolve_key(key_name)
        if pynput_key is None:
            logger.debug("Unknown key: %s", key_name)
            return
        try:
            self._kb.press(pynput_key)
            self._held_keys.add(key_name)
            logger.debug("key_down: %s", key_name)
        except Exception as exc:
            logger.warning("key_down error [%s]: %s", key_name, exc)

    def key_up(self, key_name: str):
        pynput_key = self._resolve_key(key_name)
        if pynput_key is None:
            return
        try:
            self._kb.release(pynput_key)
            self._held_keys.discard(key_name)
            logger.debug("key_up: %s", key_name)
        except Exception as exc:
            logger.warning("key_up error [%s]: %s", key_name, exc)

    def type_text(self, text: str):
        """Type a Unicode string using pynput type() — handles IME and Unicode."""
        try:
            self._kb.type(text)
        except Exception as exc:
            logger.warning("type_text error: %s", exc)

    def shortcut(self, keys: list[str]):
        """
        Execute a keyboard shortcut by pressing keys in order, then releasing in reverse.
        Example: ['ctrl', 'c'] → ctrl-down, c-down, c-up, ctrl-up
        """
        pynput_keys = [self._resolve_key(k) for k in keys]
        pynput_keys = [k for k in pynput_keys if k is not None]
        try:
            for k in pynput_keys:
                self._kb.press(k)
            for k in reversed(pynput_keys):
                self._kb.release(k)
        except Exception as exc:
            logger.warning("shortcut error %s: %s", keys, exc)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    async def release_all(self):
        """Release all held keys and mouse buttons. Called on disconnect/shutdown."""
        logger.info("Releasing all held input state.")

        # Mouse buttons
        for button in list(self._held_buttons):
            self.mouse_up(button)

        # Keyboard keys
        for key_name in list(self._held_keys):
            self.key_up(key_name)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _resolve_key(self, key_name: str):
        """Convert Orbit key name to a pynput key or KeyCode."""
        lower = key_name.lower()

        if lower in SPECIAL_KEY_MAP:
            return SPECIAL_KEY_MAP[lower]

        # Single printable character
        if len(key_name) == 1:
            return KeyCode.from_char(key_name)

        # Unknown
        return None
