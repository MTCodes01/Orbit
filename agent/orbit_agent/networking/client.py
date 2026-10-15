"""
Agent WebSocket client — handles pairing, authentication, registration,
reconnection with exponential backoff, and incoming input event routing.
"""

from __future__ import annotations

import asyncio
import json
import logging
import platform
import socket
import time
from typing import Optional

import websockets
from websockets.exceptions import ConnectionClosed

from orbit_agent.configuration.config import AgentConfig
from orbit_agent.input.injector import InputInjector
from orbit_agent.display.info import DisplayInfo

logger = logging.getLogger("orbit.client")

AGENT_VERSION = "1.0.0"
HEARTBEAT_INTERVAL = 15
INITIAL_BACKOFF = 1.0
MAX_BACKOFF = 60.0


class AgentWebSocketClient:
    def __init__(self, config: AgentConfig, injector: InputInjector, display: DisplayInfo):
        self.config = config
        self.injector = injector
        self.display = display
        self._running = False
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._reconnect_delay = INITIAL_BACKOFF
        self.on_status_change = None  # Callback for tray icon

    @property
    def ws_url(self) -> str:
        base = (self.config.backend_url or "").strip().rstrip("/")
        if base.startswith("http://"):
            base = "ws://" + base[7:]
        elif base.startswith("https://"):
            base = "wss://" + base[8:]
        elif not base.startswith("ws://") and not base.startswith("wss://"):
            base = "ws://" + base
        return base + "/ws/agent"

    @property
    def http_url(self) -> str:
        base = (self.config.backend_url or "").strip().rstrip("/")
        if base.startswith("ws://"):
            base = "http://" + base[5:]
        elif base.startswith("wss://"):
            base = "https://" + base[6:]
        elif not base.startswith("http://") and not base.startswith("https://"):
            base = "http://" + base
        return base

    def _emit_status(self, status: str):
        if self.on_status_change:
            self.on_status_change(status)

    async def run(self):
        self._running = True
        while self._running:
            try:
                await self._connect_and_run()
                self._reconnect_delay = INITIAL_BACKOFF
            except ConnectionClosed as exc:
                logger.warning("Connection closed: %s", exc)
                self._emit_status("disconnected")
                await self.injector.release_all()
            except (OSError, websockets.InvalidURI) as exc:
                logger.error("Connection error: %s", exc)
                self._emit_status("error")
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.exception("Unexpected error: %s", exc)
                self._emit_status("error")

            if self._running:
                delay = self._reconnect_delay
                logger.info("Reconnecting in %.1fs...", delay)
                self._emit_status(f"reconnecting in {int(delay)}s")
                await asyncio.sleep(delay)
                self._reconnect_delay = min(self._reconnect_delay * 2, MAX_BACKOFF)

    async def _connect_and_run(self):
        logger.info("Connecting to %s", self.ws_url)
        self._emit_status("connecting")

        async with websockets.connect(
            self.ws_url,
            ping_interval=None,  # We manage heartbeats ourselves
            max_size=2**20,
        ) as ws:
            self._ws = ws
            self._emit_status("authenticating")

            # ----------------------------------------------------------
            # Phase 1: Pair or authenticate
            # ----------------------------------------------------------
            if not self.config.is_paired:
                success = await self._pair(ws)
                if not success:
                    return
                # Successfully paired! Stored device_id and secret in config & keyring.
                # Return here so the outer run() loop immediately connects & authenticates.
                logger.info("Pairing completed. Reconnecting to authenticate.")
                return
            else:
                success = await self._authenticate(ws)
                if not success:
                    self.config.clear_pairing()
                    logger.warning("Auth failed — clearing credentials. Will re-pair.")
                    return

            self._emit_status("registering")
            await self._register(ws)
            self._emit_status("connected")
            self._reconnect_delay = INITIAL_BACKOFF

            # ----------------------------------------------------------
            # Phase 2: Main message loop + heartbeat
            # ----------------------------------------------------------
            heartbeat_task = asyncio.create_task(self._heartbeat_loop(ws))
            try:
                async for raw in ws:
                    if not isinstance(raw, str):
                        continue
                    try:
                        msg = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    await self._handle_message(msg)
            finally:
                heartbeat_task.cancel()
                await self.injector.release_all()
                self._ws = None

    async def _pair(self, ws) -> bool:
        """Enter the pairing flow — prompt user for code, send pair_request."""
        code = input("\nEnter pairing code from the Orbit PWA: ").strip()
        if not code:
            logger.error("No pairing code entered.")
            return False

        hostname = socket.gethostname()
        device_name = self.config.device_name or hostname

        await ws.send(json.dumps({
            "type": "pair_request",
            "protocol_version": "1.0.0",
            "payload": {
                "pairing_code": code,
                "device_name": device_name,
                "hostname": hostname,
                "os_info": f"Windows {platform.version()}",
                "agent_version": AGENT_VERSION,
                "screen_width": self.display.primary_width,
                "screen_height": self.display.primary_height,
            },
        }))

        logger.info("Pairing request sent. Waiting for approval in PWA...")
        print("\nWaiting for PWA approval... (approve in the Orbit app on your phone)")

        # Wait for pair_success or pair_rejected
        async for raw in ws:
            msg = json.loads(raw)
            if msg.get("type") == "pair_success":
                payload = msg.get("payload", {})
                device_id = payload.get("device_id")
                device_secret = payload.get("device_secret")
                if device_id and device_secret:
                    self.config.device_id = device_id
                    self.config.device_name = device_name
                    self.config.save()
                    self.config.store_secret(device_secret)
                    logger.info("Pairing successful. Device ID: %s", device_id)
                    print(f"\n✓ Pairing successful! Device ID: {device_id}")
                    return True
            elif msg.get("type") == "pair_rejected":
                logger.warning("Pairing rejected: %s", msg.get("reason"))
                print(f"\n✗ Pairing rejected: {msg.get('reason', 'Unknown reason')}")
                return False
            elif msg.get("type") == "error":
                logger.error("Pairing error: %s", msg.get("message"))
                print(f"\n✗ Error: {msg.get('message')}")
                return False

        return False

    async def _authenticate(self, ws) -> bool:
        """Authenticate using stored device_id + secret."""
        secret = self.config.retrieve_secret()
        if not secret:
            logger.error("No stored secret for device %s", self.config.device_id)
            return False

        await ws.send(json.dumps({
            "type": "auth_request",
            "protocol_version": "1.0.0",
            "payload": {
                "device_id": self.config.device_id,
                "device_secret": secret,
            },
        }))

        raw = await ws.recv()
        msg = json.loads(raw)
        if msg.get("type") == "auth_success":
            logger.info("Authentication successful for %s", self.config.device_id)
            return True
        else:
            logger.warning("Auth response: %s", msg.get("type"))
            return False

    async def _register(self, ws):
        """Send device_register with full metadata."""
        caps = self.display.to_dict()
        await ws.send(json.dumps({
            "type": "device_register",
            "protocol_version": "1.0.0",
            "payload": {
                "device_id": self.config.device_id,
                "friendly_name": self.config.device_name or socket.gethostname(),
                "hostname": socket.gethostname(),
                "os_info": f"Windows {platform.version()}",
                "agent_version": AGENT_VERSION,
                "screen_width": self.display.primary_width,
                "screen_height": self.display.primary_height,
                "capabilities": {
                    "supports_keyboard": True,
                    "supports_mouse": True,
                    "supports_scroll": True,
                    "supports_multi_monitor": len(self.display.monitors) > 1,
                    "monitor_count": len(self.display.monitors),
                    "monitors": caps.get("monitors", []),
                },
            },
        }))
        logger.info("Device registered with backend.")

    async def _heartbeat_loop(self, ws):
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            try:
                await ws.send(json.dumps({
                    "type": "heartbeat",
                    "protocol_version": "1.0.0",
                    "device_id": self.config.device_id,
                }))
            except Exception:
                break

    async def _handle_message(self, msg: dict):
        msg_type = msg.get("type")

        if msg_type == "heartbeat_ack":
            return

        elif msg_type == "pointer_move":
            dx = msg.get("dx", 0)
            dy = msg.get("dy", 0)
            self.injector.pointer_move(dx, dy)

        elif msg_type == "cursor_position":
            x = msg.get("x", 0)
            y = msg.get("y", 0)
            self.injector.set_cursor_position(x, y)

        elif msg_type == "switch_monitor":
            monitor_index = int(msg.get("monitor_index", 0))
            self.injector.jump_to_monitor(monitor_index, self.display.monitors)

        elif msg_type == "mouse_down":
            button = msg.get("button", "left")
            self.injector.mouse_down(button)

        elif msg_type == "mouse_up":
            button = msg.get("button", "left")
            self.injector.mouse_up(button)

        elif msg_type == "scroll":
            dx = msg.get("dx", 0)
            dy = msg.get("dy", 0)
            self.injector.scroll(dx, dy)

        elif msg_type == "key_down":
            key = msg.get("key", "")
            self.injector.key_down(key)

        elif msg_type == "key_up":
            key = msg.get("key", "")
            self.injector.key_up(key)

        elif msg_type == "text_input":
            text = msg.get("text", "")
            self.injector.type_text(text)

        elif msg_type == "shortcut":
            keys = msg.get("keys", [])
            self.injector.shortcut(keys)

        elif msg_type == "session_start":
            logger.info("Session started by controller.")
            # Future: log session, show tray indicator

        elif msg_type == "session_end":
            logger.info("Session ended.")
            await self.injector.release_all()

        elif msg_type == "topology_update":
            version = msg.get("version")
            logger.info("Topology updated to version %s", version)

        elif msg_type == "device_revoked":
            logger.warning("Device revoked by backend. Clearing credentials.")
            self.config.clear_pairing()
            await self.stop()

        elif msg_type == "latency_ping":
            # Respond with pong
            if self._ws:
                await self._ws.send(json.dumps({
                    "type": "latency_pong",
                    "protocol_version": "1.0.0",
                    "ping_id": msg.get("ping_id"),
                    "sent_ms": msg.get("sent_ms"),
                    "received_ms": int(time.time() * 1000),
                }))

        elif msg_type == "error":
            logger.error("Backend error: [%s] %s", msg.get("code"), msg.get("message"))

        else:
            logger.debug("Unhandled message type: %s", msg_type)

    async def stop(self):
        self._running = False
        if self._ws:
            await self._ws.close()
