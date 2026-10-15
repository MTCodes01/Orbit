"""
Windows Input Handler using Win32 SendInput API.
Ultra-low latency mouse, keyboard, and media key emulation with zero external dependencies.
"""

import ctypes
from ctypes import wintypes
import time
from typing import Optional, List

# Win32 Constants
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
INPUT_HARDWARE = 2

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_HWHEEL = 0x1000
MOUSEEVENTF_ABSOLUTE = 0x8000

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_SCANCODE = 0x0008

WHEEL_DELTA = 120

# Virtual Key Codes
VK_MAP = {
    # Modifiers
    'shift': 0x10,
    'lshift': 0xA0,
    'rshift': 0xA1,
    'ctrl': 0x11,
    'lctrl': 0xA2,
    'rctrl': 0xA3,
    'alt': 0x12,
    'win': 0x5B,
    'lwin': 0x5B,
    'rwin': 0x5C,
    
    # Common keys
    'enter': 0x0D,
    'return': 0x0D,
    'esc': 0x1B,
    'escape': 0x1B,
    'backspace': 0x08,
    'tab': 0x09,
    'space': 0x20,
    'delete': 0x2E,
    'insert': 0x2D,
    'capslock': 0x14,
    'printscreen': 0x2C,
    'prtscn': 0x2C,
    
    # Navigation
    'left': 0x25,
    'up': 0x26,
    'right': 0x27,
    'down': 0x28,
    'home': 0x24,
    'end': 0x23,
    'pageup': 0x21,
    'pgup': 0x21,
    'pagedown': 0x22,
    'pgdn': 0x22,
    
    # Media Keys
    'volumedown': 0xAE,
    'volumeup': 0xAF,
    'volumemute': 0xAD,
    'mute': 0xAD,
    'mediaplaypause': 0xB3,
    'playpause': 0xB3,
    'medianexttrack': 0xB0,
    'nexttrack': 0xB0,
    'mediaprevtrack': 0xB1,
    'prevtrack': 0xB1,
    'mediastop': 0xB2,
    
    # Function Keys
    'f1': 0x70, 'f2': 0x71, 'f3': 0x72, 'f4': 0x73,
    'f5': 0x74, 'f6': 0x75, 'f7': 0x76, 'f8': 0x77,
    'f9': 0x78, 'f10': 0x79, 'f11': 0x7A, 'f12': 0x7B,
}

# Add letters A-Z
for i in range(26):
    char = chr(ord('a') + i)
    VK_MAP[char] = 0x41 + i

# Add digits 0-9
for i in range(10):
    char = str(i)
    VK_MAP[char] = 0x30 + i


# ctypes structs for Win32 SendInput
class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ('dx', wintypes.LONG),
        ('dy', wintypes.LONG),
        ('mouseData', wintypes.DWORD),
        ('dwFlags', wintypes.DWORD),
        ('time', wintypes.DWORD),
        ('dwExtraInfo', ctypes.c_size_t),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ('wVk', wintypes.WORD),
        ('wScan', wintypes.WORD),
        ('dwFlags', wintypes.DWORD),
        ('time', wintypes.DWORD),
        ('dwExtraInfo', ctypes.c_size_t),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ('uMsg', wintypes.DWORD),
        ('wParamL', wintypes.WORD),
        ('wParamH', wintypes.WORD),
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [
        ('mi', MOUSEINPUT),
        ('ki', KEYBDINPUT),
        ('hi', HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _fields_ = [
        ('type', wintypes.DWORD),
        ('u', _INPUT_UNION),
    ]


LPINPUT = ctypes.POINTER(INPUT)
SendInput = ctypes.windll.user32.SendInput
SendInput.argtypes = [wintypes.UINT, LPINPUT, ctypes.c_int]
SendInput.restype = wintypes.UINT


class InputManager:
    """Manages low-level Windows keyboard and mouse events."""

    def __init__(self):
        self.user32 = ctypes.windll.user32
        self.screen_width = self.user32.GetSystemMetrics(0)
        self.screen_height = self.user32.GetSystemMetrics(1)
        self._drag_active = False
        self._subpixel_x = 0.0
        self._subpixel_y = 0.0

    def mouse_move(self, dx: float, dy: float, acceleration: float = 1.0):
        """Relative cursor move with acceleration and subpixel accumulator."""
        self._subpixel_x += dx * acceleration
        self._subpixel_y += dy * acceleration

        scaled_dx = int(self._subpixel_x)
        scaled_dy = int(self._subpixel_y)

        if scaled_dx == 0 and scaled_dy == 0:
            return

        self._subpixel_x -= scaled_dx
        self._subpixel_y -= scaled_dy

        inp = INPUT()
        inp.type = INPUT_MOUSE
        inp.u.mi.dx = scaled_dx
        inp.u.mi.dy = scaled_dy
        inp.u.mi.mouseData = 0
        inp.u.mi.dwFlags = MOUSEEVENTF_MOVE
        inp.u.mi.time = 0
        inp.u.mi.dwExtraInfo = 0

        SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

    def mouse_button(self, button: str, action: str):
        """
        button: 'left', 'right', 'middle'
        action: 'down', 'up', 'click', 'dblclick'
        """
        flags_down = {
            'left': MOUSEEVENTF_LEFTDOWN,
            'right': MOUSEEVENTF_RIGHTDOWN,
            'middle': MOUSEEVENTF_MIDDLEDOWN,
        }
        flags_up = {
            'left': MOUSEEVENTF_LEFTUP,
            'right': MOUSEEVENTF_RIGHTUP,
            'middle': MOUSEEVENTF_MIDDLEUP,
        }

        btn = button.lower()
        if btn not in flags_down:
            return

        if action == 'down':
            self._send_mouse_flag(flags_down[btn])
        elif action == 'up':
            self._send_mouse_flag(flags_up[btn])
        elif action == 'click':
            self._send_mouse_flag(flags_down[btn])
            time.sleep(0.01)
            self._send_mouse_flag(flags_up[btn])
        elif action == 'dblclick':
            self._send_mouse_flag(flags_down[btn])
            self._send_mouse_flag(flags_up[btn])
            time.sleep(0.05)
            self._send_mouse_flag(flags_down[btn])
            self._send_mouse_flag(flags_up[btn])

    def mouse_scroll(self, dx: float, dy: float):
        """Scroll vertical and horizontal."""
        if dy != 0:
            # Positive dy scrolls up, negative down
            wheel_amount = int(dy * (WHEEL_DELTA / 3))
            inp = INPUT()
            inp.type = INPUT_MOUSE
            inp.u.mi.dx = 0
            inp.u.mi.dy = 0
            inp.u.mi.mouseData = wheel_amount
            inp.u.mi.dwFlags = MOUSEEVENTF_WHEEL
            inp.u.mi.time = 0
            inp.u.mi.dwExtraInfo = 0
            SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

        if dx != 0:
            hwheel_amount = int(dx * (WHEEL_DELTA / 3))
            inp = INPUT()
            inp.type = INPUT_MOUSE
            inp.u.mi.dx = 0
            inp.u.mi.dy = 0
            inp.u.mi.mouseData = hwheel_amount
            inp.u.mi.dwFlags = MOUSEEVENTF_HWHEEL
            inp.u.mi.time = 0
            inp.u.mi.dwExtraInfo = 0
            SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

    def mouse_zoom(self, delta: float):
        """Pinch-to-zoom (Ctrl + Wheel)."""
        self.key_event('ctrl', 'down')
        try:
            self.mouse_scroll(0, delta)
        finally:
            self.key_event('ctrl', 'up')

    def toggle_drag(self) -> bool:
        """Toggle left mouse button down/up for drag lock."""
        if self._drag_active:
            self.mouse_button('left', 'up')
            self._drag_active = False
        else:
            self.mouse_button('left', 'down')
            self._drag_active = True
        return self._drag_active

    def _send_mouse_flag(self, flag: int):
        inp = INPUT()
        inp.type = INPUT_MOUSE
        inp.u.mi.dx = 0
        inp.u.mi.dy = 0
        inp.u.mi.mouseData = 0
        inp.u.mi.dwFlags = flag
        inp.u.mi.time = 0
        inp.u.mi.dwExtraInfo = 0
        SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

    def key_event(self, key_name: str, action: str):
        """
        key_name: name in VK_MAP or single char
        action: 'down', 'up', 'tap'
        """
        k = key_name.lower().strip()
        vk = VK_MAP.get(k)
        if vk is None:
            # If it's a single unicode char, type it as unicode
            if len(key_name) == 1:
                self.type_unicode_char(key_name)
            return

        is_extended = vk in (0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x2D, 0x2E, 0x5B, 0x5C, 0xAE, 0xAF, 0xAD, 0xB0, 0xB1, 0xB2, 0xB3)

        if action == 'down':
            self._send_key_event(vk, down=True, extended=is_extended)
        elif action == 'up':
            self._send_key_event(vk, down=False, extended=is_extended)
        elif action == 'tap':
            self._send_key_event(vk, down=True, extended=is_extended)
            time.sleep(0.015)
            self._send_key_event(vk, down=False, extended=is_extended)

    def hotkey(self, keys: List[str]):
        """Press and release a combination of keys (e.g. ['ctrl', 'c'])."""
        for k in keys:
            self.key_event(k, 'down')
            time.sleep(0.01)
        for k in reversed(keys):
            self.key_event(k, 'up')
            time.sleep(0.01)

    def type_unicode_char(self, char: str):
        """Send a single unicode character."""
        code = ord(char)
        # Key down
        inp_down = INPUT()
        inp_down.type = INPUT_KEYBOARD
        inp_down.u.ki.wVk = 0
        inp_down.u.ki.wScan = code
        inp_down.u.ki.dwFlags = KEYEVENTF_UNICODE
        inp_down.u.ki.time = 0
        inp_down.u.ki.dwExtraInfo = 0

        # Key up
        inp_up = INPUT()
        inp_up.type = INPUT_KEYBOARD
        inp_up.u.ki.wVk = 0
        inp_up.u.ki.wScan = code
        inp_up.u.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
        inp_up.u.ki.time = 0
        inp_up.u.ki.dwExtraInfo = 0

        inputs = (INPUT * 2)(inp_down, inp_up)
        SendInput(2, inputs, ctypes.sizeof(INPUT))

    def type_text(self, text: str):
        """Type a full string of text via unicode events."""
        for char in text:
            if char == '\n':
                self.key_event('enter', 'tap')
            elif char == '\t':
                self.key_event('tab', 'tap')
            else:
                self.type_unicode_char(char)
            time.sleep(0.005)

    def _send_key_event(self, vk: int, down: bool, extended: bool = False):
        flags = 0
        if not down:
            flags |= KEYEVENTF_KEYUP
        if extended:
            flags |= KEYEVENTF_EXTENDEDKEY

        inp = INPUT()
        inp.type = INPUT_KEYBOARD
        inp.u.ki.wVk = vk
        inp.u.ki.wScan = 0
        inp.u.ki.dwFlags = flags
        inp.u.ki.time = 0
        inp.u.ki.dwExtraInfo = 0

        SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


# Singleton instance
input_manager = InputManager()
