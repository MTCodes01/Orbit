"""Tests for Orbit Windows Agent core components."""

import json
from unittest.mock import MagicMock, patch
import pytest

from orbit_agent.configuration.config import AgentConfig, KEYRING_SERVICE
from orbit_agent.input.injector import InputInjector, SPECIAL_KEY_MAP


def test_agent_config_defaults():
    cfg = AgentConfig()
    assert cfg.backend_url == ""
    assert cfg.device_id is None
    assert cfg.device_name == ""
    assert cfg.is_paired is False


def test_agent_config_save_load(tmp_path):
    config_file = tmp_path / "config.json"
    cfg = AgentConfig(backend_url="http://192.168.1.10:8000", device_id="test-id", device_name="Test Laptop")
    cfg._config_path = config_file
    cfg.save()

    assert config_file.exists()
    data = json.loads(config_file.read_text(encoding="utf-8"))
    assert data["backend_url"] == "http://192.168.1.10:8000"
    assert data["device_id"] == "test-id"
    assert data["device_name"] == "Test Laptop"
    assert cfg.is_paired is True


@patch("keyring.set_password")
@patch("keyring.get_password")
@patch("keyring.delete_password")
def test_agent_config_keyring(mock_del, mock_get, mock_set):
    cfg = AgentConfig(device_id="dev-123")
    cfg.store_secret("secret-token-xyz")
    mock_set.assert_called_once_with(KEYRING_SERVICE, "dev-123", "secret-token-xyz")

    mock_get.return_value = "secret-token-xyz"
    assert cfg.retrieve_secret() == "secret-token-xyz"
    mock_get.assert_called_once_with(KEYRING_SERVICE, "dev-123")

    cfg.delete_secret()
    mock_del.assert_called_once_with(KEYRING_SERVICE, "dev-123")


@patch("ctypes.windll.user32.mouse_event")
def test_input_injector_pointer_move(mock_mouse_event):
    injector = InputInjector()
    injector.pointer_move(50, -30)
    mock_mouse_event.assert_called_once_with(0x0001, 50, -30, 0, 0)


@patch("pyautogui.size", return_value=(1920, 1080))
@patch("pyautogui.mouseDown")
@patch("pyautogui.mouseUp")
@pytest.mark.asyncio
async def test_input_injector_mouse_and_release_all(mock_up, mock_down, mock_size):
    injector = InputInjector()
    injector.mouse_down("left")
    assert "left" in injector._held_buttons
    mock_down.assert_called_once_with(button="left", _pause=False)

    await injector.release_all()
    assert len(injector._held_buttons) == 0
    mock_up.assert_called_once_with(button="left", _pause=False)


def test_special_key_map():
    assert "escape" in SPECIAL_KEY_MAP
    assert "enter" in SPECIAL_KEY_MAP
    assert "ctrl" in SPECIAL_KEY_MAP
    assert "alt" in SPECIAL_KEY_MAP
    assert "f1" in SPECIAL_KEY_MAP
    assert "f12" in SPECIAL_KEY_MAP


@patch("orbit_agent.configuration.autostart.winreg", create=True)
def test_autostart_logic(mock_winreg):
    from orbit_agent.configuration.autostart import is_autostart_enabled, set_autostart
    
    # Test enable
    success = set_autostart(True, exe_path="C:\\Orbit\\orbit-agent.exe")
    assert success is True

    # Test disable
    success_disable = set_autostart(False)
    assert success_disable is True


def test_agent_client_url_formatting():
    from orbit_agent.networking.client import AgentWebSocketClient
    from orbit_agent.display.info import DisplayInfo

    disp = DisplayInfo(primary_width=1920, primary_height=1080)

    # Case 1: IP without scheme
    c1 = AgentConfig(backend_url="192.168.29.32:8000")
    client1 = AgentWebSocketClient(c1, MagicMock(), disp)
    assert client1.ws_url == "ws://192.168.29.32:8000/ws/agent"
    assert client1.http_url == "http://192.168.29.32:8000"

    # Case 2: http:// URL with trailing slash
    c2 = AgentConfig(backend_url="http://10.0.0.5:8000/")
    client2 = AgentWebSocketClient(c2, MagicMock(), disp)
    assert client2.ws_url == "ws://10.0.0.5:8000/ws/agent"
    assert client2.http_url == "http://10.0.0.5:8000"

    # Case 3: https:// URL
    c3 = AgentConfig(backend_url="https://orbit.example.com")
    client3 = AgentWebSocketClient(c3, MagicMock(), disp)
    assert client3.ws_url == "wss://orbit.example.com/ws/agent"
    assert client3.http_url == "https://orbit.example.com"


@patch("ctypes.windll.user32.SetCursorPos")
@patch("ctypes.windll.user32.mouse_event")
def test_input_injector_multi_monitor(mock_mouse_event, mock_set_cursor):
    from orbit_agent.input.injector import InputInjector
    from orbit_agent.display.info import MonitorInfo

    injector = InputInjector()
    # Moving left by 100px and down by 50px passes relative delta directly to Windows
    injector.pointer_move(-100, 50)
    mock_mouse_event.assert_called_with(0x0001, -100, 50, 0, 0)

    # Test jump_to_monitor
    monitors = [
        MonitorInfo(index=0, width=1920, height=1080, x=-1920, y=0, is_primary=False),
        MonitorInfo(index=1, width=1920, height=1080, x=0, y=0, is_primary=True),
    ]
    injector.jump_to_monitor(0, monitors)
    # Center of monitor 0 is -1920 + 960 = -960, y = 540
    mock_set_cursor.assert_called_with(-960, 540)


