"""
Virtual Gamepad Controller Handler.
Supports native Virtual Xbox 360 controller emulation via ViGEmBus (vgamepad),
with seamless fallback to direct keyboard/mouse gamepad mapping if ViGEmBus is not yet installed.
"""

import sys
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("controller_handler")

# Attempt to load vgamepad
VGAMEPAD_AVAILABLE = False
vg = None
try:
    import vgamepad as _vg
    vg = _vg
    VGAMEPAD_AVAILABLE = True
except Exception as e:
    logger.info(f"vgamepad module could not be loaded: {e}")


class ControllerManager:
    """Handles virtual controller events from phone client."""

    def __init__(self, input_manager=None):
        self.input_manager = input_manager
        self.gamepad = None
        self.is_vigem_active = False
        self.init_error = None
        self.mode = "fallback"  # 'vigem' or 'fallback'
        
        # State tracking for fallback
        self._fallback_pressed_keys = set()
        
        # Try initializing ViGEm gamepad
        self.try_init_vigem()

    def try_init_vigem(self) -> bool:
        """Attempt to connect to ViGEmBus virtual Xbox 360 controller."""
        if not VGAMEPAD_AVAILABLE or vg is None:
            self.mode = "fallback"
            self.init_error = "vgamepad module unavailable"
            return False

        try:
            self.gamepad = vg.VX360Gamepad()
            self.is_vigem_active = True
            self.mode = "vigem"
            self.init_error = None
            logger.info("Successfully initialized Virtual Xbox 360 Controller (ViGEmBus)!")
            return True
        except Exception as e:
            self.gamepad = None
            self.is_vigem_active = False
            self.mode = "fallback"
            self.init_error = str(e)
            logger.warning(f"ViGEmBus driver not active ({e}). Operating in Gamepad Fallback Mode.")
            return False

    def handle_event(self, event_type: str, data: Dict[str, Any]):
        """
        Handle incoming controller events:
        - 'button': {'button': 'A', 'state': 'down'|'up'}
        - 'stick': {'stick': 'left'|'right', 'x': float, 'y': float}
        - 'trigger': {'trigger': 'left'|'right', 'value': float}
        - 'dpad': {'direction': 'up'|'down'|'left'|'right', 'state': 'down'|'up'}
        """
        if self.mode == "vigem" and self.gamepad is not None:
            self._handle_vigem_event(event_type, data)
        else:
            self._handle_fallback_event(event_type, data)

    def _handle_vigem_event(self, event_type: str, data: Dict[str, Any]):
        try:
            if event_type == "button":
                btn_name = data.get("button", "").upper()
                state = data.get("state", "down")
                btn_map = {
                    "A": vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
                    "B": vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
                    "X": vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
                    "Y": vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
                    "LB": vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
                    "RB": vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
                    "START": vg.XUSB_BUTTON.XUSB_GAMEPAD_START,
                    "BACK": vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK,
                    "GUIDE": vg.XUSB_BUTTON.XUSB_GAMEPAD_GUIDE,
                    "LS": vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB,
                    "RS": vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB,
                }
                btn = btn_map.get(btn_name)
                if btn:
                    if state == "down":
                        self.gamepad.press_button(button=btn)
                    else:
                        self.gamepad.release_button(button=btn)
                    self.gamepad.update()

            elif event_type == "dpad":
                direction = data.get("direction", "").upper()
                state = data.get("state", "down")
                dpad_map = {
                    "UP": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP,
                    "DOWN": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN,
                    "LEFT": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT,
                    "RIGHT": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT,
                }
                btn = dpad_map.get(direction)
                if btn:
                    if state == "down":
                        self.gamepad.press_button(button=btn)
                    else:
                        self.gamepad.release_button(button=btn)
                    self.gamepad.update()

            elif event_type == "stick":
                stick = data.get("stick", "left")
                # X: -1.0 to 1.0, Y: -1.0 to 1.0 (invert Y for typical game coordinates if needed)
                x = float(data.get("x", 0.0))
                y = float(data.get("y", 0.0))
                
                # Clamp between -1.0 and 1.0
                x = max(-1.0, min(1.0, x))
                y = max(-1.0, min(1.0, y))

                if stick == "left":
                    self.gamepad.left_joystick_float(x_value_float=x, y_value_float=y)
                elif stick == "right":
                    self.gamepad.right_joystick_float(x_value_float=x, y_value_float=y)
                self.gamepad.update()

            elif event_type == "trigger":
                trigger = data.get("trigger", "left")
                value = float(data.get("value", 0.0))
                value = max(0.0, min(1.0, value))

                if trigger == "left":
                    self.gamepad.left_trigger_float(value_float=value)
                elif trigger == "right":
                    self.gamepad.right_trigger_float(value_float=value)
                self.gamepad.update()

        except Exception as e:
            logger.error(f"Error handling ViGEm event: {e}")

    def _handle_fallback_event(self, event_type: str, data: Dict[str, Any]):
        """Map gamepad controls to standard keyboard and mouse inputs."""
        if not self.input_manager:
            return

        try:
            if event_type == "button":
                btn = data.get("button", "").upper()
                state = data.get("state", "down")
                mapping = {
                    "A": ("space", "key"),
                    "B": ("shift", "key"),
                    "X": ("e", "key"),
                    "Y": ("r", "key"),
                    "LB": ("q", "key"),
                    "RB": ("tab", "key"),
                    "START": ("esc", "key"),
                    "BACK": ("m", "key"),
                    "LS": ("c", "key"),
                    "RS": ("v", "key"),
                }
                mapped = mapping.get(btn)
                if mapped:
                    target_key, kind = mapped
                    if kind == "key":
                        self.input_manager.key_event(target_key, state)

            elif event_type == "dpad":
                direction = data.get("direction", "").lower()
                state = data.get("state", "down")
                # Arrow keys
                if direction in ["up", "down", "left", "right"]:
                    self.input_manager.key_event(direction, state)

            elif event_type == "stick":
                stick = data.get("stick", "left")
                x = float(data.get("x", 0.0))
                y = float(data.get("y", 0.0))
                deadzone = 0.25

                if stick == "left":
                    # Map Left Stick to WASD
                    # W / S
                    if y > deadzone:
                        self.input_manager.key_event("w", "down")
                        self._fallback_pressed_keys.add("w")
                    elif "w" in self._fallback_pressed_keys:
                        self.input_manager.key_event("w", "up")
                        self._fallback_pressed_keys.discard("w")

                    if y < -deadzone:
                        self.input_manager.key_event("s", "down")
                        self._fallback_pressed_keys.add("s")
                    elif "s" in self._fallback_pressed_keys:
                        self.input_manager.key_event("s", "up")
                        self._fallback_pressed_keys.discard("s")

                    # A / D
                    if x < -deadzone:
                        self.input_manager.key_event("a", "down")
                        self._fallback_pressed_keys.add("a")
                    elif "a" in self._fallback_pressed_keys:
                        self.input_manager.key_event("a", "up")
                        self._fallback_pressed_keys.discard("a")

                    if x > deadzone:
                        self.input_manager.key_event("d", "down")
                        self._fallback_pressed_keys.add("d")
                    elif "d" in self._fallback_pressed_keys:
                        self.input_manager.key_event("d", "up")
                        self._fallback_pressed_keys.discard("d")

                elif stick == "right":
                    # Right stick moves mouse view
                    if abs(x) > deadzone or abs(y) > deadzone:
                        dx = x * 15
                        dy = -y * 15
                        self.input_manager.mouse_move(dx, dy)

            elif event_type == "trigger":
                trigger = data.get("trigger", "left")
                val = float(data.get("value", 0.0))
                threshold = 0.5
                btn = "right" if trigger == "left" else "left"  # LT = Aim (RMB), RT = Shoot (LMB)
                
                if val >= threshold:
                    self.input_manager.mouse_button(btn, "down")
                else:
                    self.input_manager.mouse_button(btn, "up")

        except Exception as e:
            logger.error(f"Error handling fallback event: {e}")

    def get_status(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "vigem_active": self.is_vigem_active,
            "init_error": self.init_error,
            "description": "Virtual Xbox 360 Controller (ViGEmBus)" if self.is_vigem_active else "Direct Keyboard/Mouse Fallback Mode"
        }
