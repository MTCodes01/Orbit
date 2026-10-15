"""
FastAPI Server with WebSockets for Laptop Remote Control.
Handles mouse, keyboard, virtual gamepad, Bluetooth audio controls,
and live interactive screen streaming with touch support.
"""

import os
import sys
import json
import time
import socket
import asyncio
import logging
from typing import Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from backend.input_handler import input_manager
from backend.controller_handler import ControllerManager
from backend.bluetooth_handler import bluetooth_handler
from backend.screen_handler import screen_manager
from backend.startup_manager import is_startup_enabled, set_startup, toggle_startup

# Set input_manager reference on handlers
controller_manager = ControllerManager(input_manager=input_manager)
bluetooth_handler.input_manager = input_manager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("server")

app = FastAPI(title="Laptop Remote Control Server", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_resource_path(relative_path: str) -> str:
    """Resolve resource path for both script and PyInstaller frozen execution."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", relative_path))


STATIC_DIR = get_resource_path("static")
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
        "controller": controller_status,
        "startup": is_startup_enabled(),
    }


@app.get("/api/startup")
async def get_startup_status():
    """Check if startup on Windows boot is enabled."""
    return {"enabled": is_startup_enabled()}


@app.post("/api/startup")
async def update_startup_status(request: Request):
    """Enable or disable startup on Windows boot."""
    data = await request.json()
    enable = bool(data.get("enabled", True))
    set_startup(enable)
    return {"enabled": is_startup_enabled()}


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


# --- Screen Capture REST Endpoints ---

@app.get("/api/screen/monitors")
async def get_screen_monitors():
    """Return all detected displays, their coordinates, and the primary monitor index."""
    monitors = screen_manager.get_monitors_list()
    primary_idx = screen_manager.get_primary_monitor_index()
    active_idx = screen_manager.selected_monitor_idx if screen_manager.selected_monitor_idx is not None else primary_idx
    return {
        "monitors": monitors,
        "primary_id": primary_idx,
        "active_id": active_idx,
        "bounds": screen_manager.active_monitor_bounds
    }


@app.get("/api/screen/snapshot")
async def get_screen_snapshot(scale: float = 0.75, quality: int = 60, monitor: int = None):
    """Capture a single JPEG snapshot of the laptop screen."""
    loop = asyncio.get_running_loop()
    frame = await loop.run_in_executor(None, screen_manager.capture_frame, scale, quality, monitor)
    if frame:
        return Response(content=frame, media_type="image/jpeg")
    return JSONResponse(status_code=500, content={"error": "Screen capture failed"})


@app.get("/api/screen/stream.mjpg")
async def get_screen_mjpeg_stream(scale: float = 0.70, quality: int = 50, fps: int = 20, monitor: int = None):
    """MJPEG stream endpoint for universal browser streaming."""
    async def frame_generator():
        target_fps = max(5, min(fps, 30))
        interval = 1.0 / target_fps
        loop = asyncio.get_running_loop()
        while True:
            t0 = time.time()
            frame = await loop.run_in_executor(None, screen_manager.capture_frame, scale, quality, monitor)
            if frame:
                yield (b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
            elapsed = time.time() - t0
            await asyncio.sleep(max(0.01, interval - elapsed))

    return StreamingResponse(
        frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


# --- Dedicated High-Performance Screen WebSocket ---

@app.websocket("/ws/screen")
async def websocket_screen_endpoint(websocket: WebSocket):
    """
    Dedicated binary WebSocket stream for ultra-low latency screen mirroring
    and direct touchscreen interactions with multi-monitor support.
    """
    await websocket.accept()
    logger.info("Screen stream client connected")

    primary_idx = screen_manager.get_primary_monitor_index()
    cfg = {
        "active": True,
        "fps": 25,
        "scale": 0.75,
        "quality": 55,
        "monitor": primary_idx,
    }
    screen_manager.set_active_monitor(primary_idx)

    loop = asyncio.get_running_loop()

    async def stream_frames():
        while cfg["active"]:
            t0 = time.time()
            frame = await loop.run_in_executor(
                None, screen_manager.capture_frame, cfg["scale"], cfg["quality"], cfg["monitor"]
            )
            if frame:
                try:
                    await websocket.send_bytes(frame)
                except Exception:
                    break

            fps = max(5, min(cfg["fps"], 35))
            interval = 1.0 / fps
            elapsed = time.time() - t0
            await asyncio.sleep(max(0.005, interval - elapsed))

    async def receive_messages():
        try:
            while True:
                data = await websocket.receive_text()
                msg = json.loads(data)
                mtype = msg.get("type")

                if mtype == "config":
                    if "monitor" in msg:
                        cfg["monitor"] = int(msg["monitor"])
                        screen_manager.set_active_monitor(cfg["monitor"])
                    if "fps" in msg:
                        cfg["fps"] = int(msg["fps"])
                    if "scale" in msg:
                        cfg["scale"] = float(msg["scale"])
                    if "quality" in msg:
                        cfg["quality"] = int(msg["quality"])

                elif mtype == "stop":
                    cfg["active"] = False

                elif mtype == "start":
                    cfg["active"] = True

                elif mtype == "touch":
                    action = msg.get("action", "click")
                    x = float(msg.get("x", 0))
                    y = float(msg.get("y", 0))
                    btn = msg.get("button", "left")
                    bounds = screen_manager.active_monitor_bounds
                    input_manager.touch_action(action, x, y, btn, bounds=bounds)

                elif mtype == "mouse_scroll":
                    dx = float(msg.get("dx", 0))
                    dy = float(msg.get("dy", 0))
                    input_manager.mouse_scroll(dx, dy)

                elif mtype == "key":
                    key_name = msg.get("key", "")
                    action = msg.get("action", "tap")
                    input_manager.key_event(key_name, action)

                elif mtype == "hotkey":
                    keys = msg.get("keys", [])
                    if isinstance(keys, list):
                        input_manager.hotkey(keys)

                elif mtype == "type_text":
                    input_manager.type_text(msg.get("text", ""))

        except (WebSocketDisconnect, asyncio.CancelledError):
            pass
        except Exception as e:
            logger.debug(f"Screen websocket recv error: {e}")
        finally:
            cfg["active"] = False

    stream_task = asyncio.create_task(stream_frames())
    recv_task = asyncio.create_task(receive_messages())

    try:
        done, pending = await asyncio.wait(
            [stream_task, recv_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending:
            task.cancel()
    except Exception:
        pass
    finally:
        logger.info("Screen stream client disconnected")


# --- Main Low-Latency Control WebSocket Handler ---

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("Client connected via main WebSocket")

    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                msg = json.loads(raw_data)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type")

            # 1. Mouse & Touch Events
            if msg_type == "mouse_move":
                dx = float(msg.get("dx", 0))
                dy = float(msg.get("dy", 0))
                accel = float(msg.get("accel", 1.0))
                input_manager.mouse_move(dx, dy, accel)

            elif msg_type == "screen_touch":
                action = msg.get("action", "click")
                x = float(msg.get("x", 0))
                y = float(msg.get("y", 0))
                btn = msg.get("button", "left")
                bounds = screen_manager.active_monitor_bounds
                input_manager.touch_action(action, x, y, btn, bounds=bounds)

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
