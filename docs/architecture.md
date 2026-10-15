# Orbit Architecture & System Design

## 1. Overview

Orbit is a real-time, low-latency multi-device remote control architecture composed of three main tiers:

1. **Controller Tier (PWA)**: Mobile web application acting as the physical human interface device (touchpad, keyboard, layout visualizer).
2. **Coordinator Tier (FastAPI Backend)**: Central rendezvous, session router, pairing authority, and topology keeper.
3. **Agent Tier (Windows Service / EXE)**: Background agent executing on each target laptop, translating protocol messages into direct Windows input injection events via Win32 APIs.

---

## 2. Component Boundaries & Responsibilities

### 2.1 PWA Controller
- **Touch Normalization**: Translates raw pointer/touch coordinates into delta movements with configurable velocity acceleration curves.
- **Gesture Detection**: Distinguishes single-tap (click), double-tap (double click), two-finger tap (right click), two-finger swipe (scroll wheel), and tap-and-hold (drag).
- **Session State**: Maintains local device list, active device focus, and dynamic virtual layout topology.
- **Zero-Install Deployment**: Delivered as standard modern web assets with offline cache fallback and Web App Manifest.

### 2.2 Coordinator Backend
- **Connection Registry (`ConnectionManager`)**: Manages concurrent WebSocket connections for both controllers and agents. Tracks active sockets, ping/pong health, and latency statistics.
- **Target Routing**: Dynamically directs incoming controller input frames (`pointer_move`, `mouse_down`, `mouse_up`, `key_down`, `key_up`, `text_input`, etc.) to the specific target agent's channel without unneeded serialization overhead.
- **Topology & Virtual Space Engine**: Stores normalized coordinate bounds for all paired displays. Facilitates cross-screen cursor handoff logic when the cursor transitions across borders.
- **Pairing Broker**: Manages ephemeral 6-digit challenge tokens, enforces rate limits, and persists authenticated device credentials.

### 2.3 Windows Agent
- **Native Input Injection**: Uses `pyautogui` and `pynput` with native Win32 platform integration (`SendInput`) for smooth cursor positioning and keyboard events.
- **Failsafe & State Reclamation**: Maintains an active ledger of pressed keys and mouse buttons. Automatically triggers `release_all()` upon packet timeout, network disconnect, or process termination to prevent keyboard or mouse locks.
- **Display Topology Discovery**: Queries multi-monitor configurations and primary display resolutions via `win32api.EnumDisplayMonitors` / `GetSystemMetrics`.
- **System Tray Host**: Non-intrusive Windows system tray integration via `pystray` with quick status inspection, reconnect triggers, and clean exit.

---

## 3. Communication Protocol

All communication between the controller, coordinator, and agent flows over WebSockets using JSON payloads adhering to the versioned schema:

```json
{
  "type": "pointer_move",
  "protocol_version": "1.0.0",
  "target_device_id": "laptop-uuid-123",
  "dx": 14.5,
  "dy": -8.2,
  "timestamp": 1728950400123
}
```

Detailed message definitions are formalized in `protocol/schemas/messages.py` and documented in `protocol/documentation/protocol.md`.
