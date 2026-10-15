"""Tests for Orbit protocol schemas and serialization."""

import pytest
from protocol.schemas.messages import (
    PointerMove,
    MouseDown,
    MouseUp,
    Scroll,
    KeyDown,
    KeyUp,
    TextInput,
    Shortcut,
    DeviceRegister,
    DeviceRegisterPayload,
    DeviceCapabilities,
    DeviceList,
    TopologyUpdate,
    MouseButton,
    MessageType,
)


def test_pointer_move_schema():
    msg = PointerMove(
        target_device_id="dev-123",
        dx=12.5,
        dy=-4.0,
    )
    data = msg.model_dump()
    assert data["type"] == MessageType.POINTER_MOVE
    assert data["target_device_id"] == "dev-123"
    assert data["dx"] == 12.5
    assert data["dy"] == -4.0
    assert data["protocol_version"] == "1.0.0"


def test_mouse_button_schemas():
    down = MouseDown(target_device_id="dev-123", button=MouseButton.LEFT)
    up = MouseUp(target_device_id="dev-123", button=MouseButton.LEFT)
    assert down.button == MouseButton.LEFT
    assert up.button == MouseButton.LEFT


def test_scroll_schema():
    scroll = Scroll(target_device_id="dev-1", dx=0, dy=120)
    assert scroll.dy == 120


def test_keyboard_schemas():
    kdown = KeyDown(target_device_id="dev-1", key="escape")
    assert kdown.key == "escape"

    text = TextInput(target_device_id="dev-1", text="Hello Orbit 🪐")
    assert text.text == "Hello Orbit 🪐"

    sc = Shortcut(target_device_id="dev-1", keys=["ctrl", "shift", "t"])
    assert sc.keys == ["ctrl", "shift", "t"]


def test_device_register_schema():
    payload = DeviceRegisterPayload(
        device_id="test-device",
        friendly_name="Work Laptop",
        hostname="WORK-PC",
        os_info="Windows 11 Pro",
        agent_version="1.0.0",
        screen_width=2560,
        screen_height=1440,
        capabilities=DeviceCapabilities(),
    )
    reg = DeviceRegister(payload=payload)
    assert reg.payload.friendly_name == "Work Laptop"
    assert reg.payload.screen_width == 2560
