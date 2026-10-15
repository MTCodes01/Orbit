"""
FastAPI Server with WebSockets for Laptop Remote Control.
Handles mouse, keyboard, virtual gamepad, and Bluetooth audio controls with sub-10ms latency.
"""

import os
import json
import socket
import logging
from typing import Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from backend.input_handler import input_manager
from backend.controller_handler import ControllerManager
from backend.bluetooth_handler import bluetooth_handler

# Set input_manager reference on handlers
controller_manager = ControllerManager(input_manager=input_manager)
bluetooth_handler.input_manager = input_manager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("server")

app = FastAPI(title="Laptop Remote Control Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static"))
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def get_local_ip() -> str:
    """Retrieve primary LAN IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


@app.get("/", response_class=HTMLResponse)
async def get_index():
    """Serve phone control web app."""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h1>Remote Control Server Ready</h1><p>index.html not found in static/</p>")


@app.get("/api/status")
async def get_system_status():
    """Retrieve full system status."""
    hostname = socket.gethostname()
    local_ip = get_local_ip()
    audio_status = bluetooth_handler.get_audio_status()
    controller_status = controller_manager.get_status()

    return {
        "hostname": hostname,
        "local_ip": local_ip,
        "screen": {
            "width": input_manager.screen_width,
            "height": input_manager.screen_height
        },
        "audio": audio_status,
        "controller": controller_status
    }


@app.get("/api/devices")
async def get_bluetooth_devices():
    """List all paired and active Bluetooth and audio devices."""
    devices = bluetooth_handler.get_devices()
    return {"devices": devices}


@app.post("/api/audio/volume")
async def set_audio_volume(request: Request):
    data = await request.json()
    level = data.get("level", 50)
    actual = bluetooth_handler.set_volume(level)
    return {"volume": actual}


@app.post("/api/audio/mute")
async def toggle_audio_mute():
    new_state = bluetooth_handler.toggle_mute()
    return {"muted": new_state}


@app.post("/api/media")
async def trigger_media_action(request: Request):
    data = await request.json()
    action = data.get("action", "")
    bluetooth_handler.media_action(action)
    return {"status": "ok", "action": action}


@app.post("/api/controller/retry")
async def retry_vigem_controller():
    success = controller_manager.try_init_vigem()
    return controller_manager.get_status()


# --- Low-Latency WebSocket Handler ---

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("Client connected via WebSocket")

    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                msg = json.loads(raw_data)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type")

            # 1. Mouse Events
            if msg_type == "mouse_move":
                dx = float(msg.get("dx", 0))
                dy = float(msg.get("dy", 0))
                accel = float(msg.get("accel", 1.0))
                input_manager.mouse_move(dx, dy, accel)

            elif msg_type == "mouse_button":
                btn = msg.get("button", "left")
                action = msg.get("action", "click")
                input_manager.mouse_button(btn, action)

            elif msg_type == "mouse_scroll":
                dx = float(msg.get("dx", 0))
                dy = float(msg.get("dy", 0))
                input_manager.mouse_scroll(dx, dy)

            elif msg_type == "mouse_zoom":
                delta = float(msg.get("delta", 0))
                input_manager.mouse_zoom(delta)

            elif msg_type == "gesture":
                action = msg.get("action", "")
                gesture_map = {
                    "task_view": ["win", "tab"],
                    "show_desktop": ["win", "d"],
                    "switch_app_next": ["alt", "tab"],
                    "switch_app_prev": ["alt", "shift", "tab"],
                    "search": ["win", "s"],
                    "action_center": ["win", "a"],
                    "desktop_next": ["ctrl", "win", "right"],
                    "desktop_prev": ["ctrl", "win", "left"],
                }
                keys = gesture_map.get(action)
                if keys:
                    input_manager.hotkey(keys)

            elif msg_type == "app_switcher_start":
                input_manager.key_event('alt', 'down')
                input_manager.key_event('tab', 'tap')

            elif msg_type == "app_switcher_step":
                direction = int(msg.get("dir", 1))
                if direction > 0:
                    input_manager.key_event('tab', 'tap')
                else:
                    input_manager.hotkey(['shift', 'tab'])

            elif msg_type == "app_switcher_end":
                input_manager.key_event('alt', 'up')

            elif msg_type == "desktop_step":
                direction = int(msg.get("dir", 1))
                if direction > 0:
                    input_manager.hotkey(['ctrl', 'win', 'right'])
                else:
                    input_manager.hotkey(['ctrl', 'win', 'left'])

            elif msg_type == "drag_toggle":
                state = input_manager.toggle_drag()
                await websocket.send_text(json.dumps({"type": "drag_state", "active": state}))

            # 2. Keyboard Events
            elif msg_type == "key":
                key_name = msg.get("key", "")
                action = msg.get("action", "tap")
                input_manager.key_event(key_name, action)

            elif msg_type == "hotkey":
                keys = msg.get("keys", [])
                if isinstance(keys, list):
                    input_manager.hotkey(keys)

            elif msg_type == "type_text":
                text = msg.get("text", "")
                input_manager.type_text(text)

            # 3. Game Controller Events
            elif msg_type == "controller_button":
                controller_manager.handle_event("button", {
                    "button": msg.get("button", ""),
                    "state": msg.get("state", "down")
                })

            elif msg_type == "controller_stick":
                controller_manager.handle_event("stick", {
                    "stick": msg.get("stick", "left"),
                    "x": float(msg.get("x", 0)),
                    "y": float(msg.get("y", 0))
                })

            elif msg_type == "controller_trigger":
                controller_manager.handle_event("trigger", {
                    "trigger": msg.get("trigger", "left"),
                    "value": float(msg.get("value", 0))
                })

            elif msg_type == "controller_dpad":
                controller_manager.handle_event("dpad", {
                    "direction": msg.get("direction", ""),
                    "state": msg.get("state", "down")
                })

            # 4. Bluetooth Audio & Media Events
            elif msg_type == "volume_set":
                vol = msg.get("value", 50)
                actual = bluetooth_handler.set_volume(vol)
                await websocket.send_text(json.dumps({"type": "volume_update", "volume": actual}))

            elif msg_type == "volume_mute_toggle":
                muted = bluetooth_handler.toggle_mute()
                await websocket.send_text(json.dumps({"type": "mute_update", "muted": muted}))

            elif msg_type == "media_action":
                act = msg.get("action", "")
                bluetooth_handler.media_action(act)

            # 5. Latency Heartbeat
            elif msg_type == "ping":
                t = msg.get("t", 0)
                await websocket.send_text(json.dumps({"type": "pong", "t": t}))

    except WebSocketDisconnect:
        input_manager.key_event('alt', 'up')
        logger.info("Client disconnected from WebSocket")
    except Exception as e:
        input_manager.key_event('alt', 'up')
        logger.error(f"WebSocket error: {e}")
