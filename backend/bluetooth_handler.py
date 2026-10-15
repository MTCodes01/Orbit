"""
Bluetooth and Audio Device Manager for Windows.
Provides real-time inspection and control of connected Bluetooth devices,
audio endpoints, volume controls, and media playback.
"""

import subprocess
import json
import logging
import ctypes
from typing import Dict, List, Any, Optional
from pycaw.pycaw import AudioUtilities

logger = logging.getLogger("bluetooth_handler")


def ensure_com():
    """Ensure COM library is initialized for the calling thread."""
    try:
        ctypes.windll.ole32.CoInitialize(None)
    except Exception:
        pass


class BluetoothAudioHandler:
    """Manages audio endpoints, master volume, and Bluetooth peripherals."""

    def __init__(self, input_manager=None):
        self.input_manager = input_manager

    def get_audio_status(self) -> Dict[str, Any]:
        """Get master volume, mute status, and current active output device."""
        ensure_com()
        try:
            speakers = AudioUtilities.GetSpeakers()
            if not speakers:
                return {"volume": 50, "muted": False, "device_name": "Default Audio Device"}
            
            vol = speakers.EndpointVolume
            master_vol = int(round(vol.GetMasterVolumeLevelScalar() * 100))
            is_muted = bool(vol.GetMute())
            device_name = speakers.FriendlyName or "Default Audio Device"

            return {
                "volume": master_vol,
                "muted": is_muted,
                "device_name": device_name
            }
        except Exception as e:
            logger.error(f"Error getting audio status: {e}")
            return {"volume": 50, "muted": False, "device_name": "Audio Device (Unknown)"}

    def set_volume(self, level_percent: int) -> int:
        """Set master volume (0 - 100)."""
        ensure_com()
        try:
            level = max(0, min(100, int(level_percent)))
            speakers = AudioUtilities.GetSpeakers()
            if speakers and speakers.EndpointVolume:
                speakers.EndpointVolume.SetMasterVolumeLevelScalar(level / 100.0, None)
            return level
        except Exception as e:
            logger.error(f"Error setting volume: {e}")
            return level_percent

    def set_mute(self, muted: bool) -> bool:
        """Set mute state."""
        ensure_com()
        try:
            speakers = AudioUtilities.GetSpeakers()
            if speakers and speakers.EndpointVolume:
                speakers.EndpointVolume.SetMute(1 if muted else 0, None)
            return muted
        except Exception as e:
            logger.error(f"Error setting mute: {e}")
            return False

    def toggle_mute(self) -> bool:
        """Toggle mute state."""
        status = self.get_audio_status()
        new_state = not status.get("muted", False)
        return self.set_mute(new_state)

    def media_action(self, action: str):
        """
        Trigger media control command:
        'playpause', 'next', 'prev', 'stop', 'volumeup', 'volumedown', 'mute'
        """
        if not self.input_manager:
            return

        action_map = {
            'playpause': 'playpause',
            'play': 'playpause',
            'pause': 'playpause',
            'next': 'nexttrack',
            'prev': 'prevtrack',
            'previous': 'prevtrack',
            'stop': 'mediastop',
            'volumeup': 'volumeup',
            'volumedown': 'volumedown',
            'mute': 'volumemute'
        }
        key = action_map.get(action.lower())
        if key:
            self.input_manager.key_event(key, 'tap')

    def get_devices(self) -> List[Dict[str, Any]]:
        """
        Returns unified list of Bluetooth devices & audio endpoints with connection states.
        """
        ensure_com()
        devices: List[Dict[str, Any]] = []
        seen_names = set()

        # 1. Inspect Audio Endpoints via Pycaw (Ultra fast)
        try:
            speakers = AudioUtilities.GetSpeakers()
            default_name = speakers.FriendlyName if speakers else ""
        except Exception:
            default_name = ""

        try:
            for dev in AudioUtilities.GetAllDevices():
                try:
                    name = dev.FriendlyName
                    if not name or name in seen_names:
                        continue

                    state_str = str(dev.state)
                    # Filter out ghost / unplugged virtual jacks
                    if "NotPresent" in state_str:
                        continue

                    is_active = "Active" in state_str
                    is_default = (name == default_name)

                    # Determine device category & icon hint
                    lower = name.lower()
                    if any(bt_hint in lower for name_part in ['mivi', 'stone', 'airdopes', 'm19', 'boat', 'jbl', 'sony', 'buds', 'airpods'] for bt_hint in [name_part]):
                        category = "bluetooth_audio"
                        icon = "headphones"
                    elif "headphone" in lower or "headset" in lower:
                        category = "headphones"
                        icon = "headphones"
                    elif "speaker" in lower:
                        category = "speakers"
                        icon = "volume-2"
                    elif "mic" in lower:
                        category = "microphone"
                        icon = "mic"
                    else:
                        category = "audio"
                        icon = "speaker"

                    seen_names.add(name)
                    devices.append({
                        "id": name,
                        "name": name,
                        "category": category,
                        "icon": icon,
                        "connected": is_active,
                        "is_default": is_default,
                        "is_bluetooth": "bluetooth" in category or "stone" in lower or "mivi" in lower or "airdopes" in lower or "m19" in lower,
                        "status_text": "Connected (Active Output)" if is_default else ("Connected" if is_active else "Paired / Disconnected")
                    })
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Error enumerating audio devices: {e}")

        # 2. Add non-audio Bluetooth peripherals (e.g. Mice, Keyboards, BLE) via PowerShell
        try:
            cmd = "powershell -NoProfile -Command \"Get-PnpDevice -Class 'Bluetooth' | Where-Object { $_.InstanceId -like 'BTHENUM*' -or $_.InstanceId -like 'BTHLE*' } | Select-Object -Property FriendlyName, Status | ConvertTo-Json\""
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=3, shell=True)
            if res.returncode == 0 and res.stdout.strip():
                pnp_data = json.loads(res.stdout)
                if isinstance(pnp_data, dict):
                    pnp_data = [pnp_data]

                for item in pnp_data:
                    fname = item.get("FriendlyName", "").strip()
                    if not fname:
                        continue
                    # Exclude low-level services
                    if any(skip in fname.lower() for skip in ["generic attribute", "generic access", "device information", "transport", "enumerator", "protocol", "service"]):
                        continue
                    
                    # Avoid duplicate if already covered by audio
                    if any(fname.lower() in d["name"].lower() for d in devices):
                        continue

                    if fname not in seen_names:
                        seen_names.add(fname)
                        devices.append({
                            "id": fname,
                            "name": fname,
                            "category": "bluetooth_peripheral",
                            "icon": "bluetooth",
                            "connected": item.get("Status") == "OK",
                            "is_default": False,
                            "is_bluetooth": True,
                            "status_text": "Paired Device"
                        })
        except Exception as e:
            logger.debug(f"PnP query skipped: {e}")

        # Sort: Default device first, then connected devices, then disconnected
        devices.sort(key=lambda d: (not d.get("is_default", False), not d.get("connected", False), d.get("name", "")))
        return devices


bluetooth_handler = BluetoothAudioHandler()
