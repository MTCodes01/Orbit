"""WebSocket connection manager for agents and controllers."""

import asyncio
import json
import logging
import time
from typing import Dict, Optional, Set

from fastapi import WebSocket

from app.core.config import settings

logger = logging.getLogger("orbit.connections")


class AgentConnection:
    """Represents one authenticated agent WebSocket connection."""

    def __init__(self, device_id: str, ws: WebSocket):
        self.device_id = device_id
        self.ws = ws
        self.connected_at = time.time()
        self.last_heartbeat = time.time()

    async def send(self, data: dict):
        try:
            await self.ws.send_text(json.dumps(data))
        except Exception as exc:
            logger.warning("Failed to send to agent %s: %s", self.device_id, exc)


class ControllerConnection:
    """Represents one authenticated controller (PWA) WebSocket connection."""

    def __init__(self, conn_id: str, ws: WebSocket):
        self.conn_id = conn_id
        self.ws = ws
        self.active_device_id: Optional[str] = None
        self.connected_at = time.time()

    async def send(self, data: dict):
        try:
            await self.ws.send_text(json.dumps(data))
        except Exception as exc:
            logger.warning("Failed to send to controller %s: %s", self.conn_id, exc)


class ConnectionManager:
    """Central registry of all live WebSocket connections."""

    def __init__(self):
        # device_id → AgentConnection
        self._agents: Dict[str, AgentConnection] = {}
        # conn_id → ControllerConnection
        self._controllers: Dict[str, ControllerConnection] = {}
        # pairing_code → WebSocket (agent waiting for user approval)
        self._pending_pairs: Dict[str, WebSocket] = {}
        # pairing_code → asyncio.Event
        self._pending_events: Dict[str, asyncio.Event] = {}
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Pending Pairing management
    # ------------------------------------------------------------------

    def register_pending_pair(self, code: str, ws: WebSocket) -> asyncio.Event:
        self._pending_pairs[code] = ws
        evt = asyncio.Event()
        self._pending_events[code] = evt
        logger.info("Registered pending pair socket for code: %s", code)
        return evt

    def unregister_pending_pair(self, code: str):
        self._pending_pairs.pop(code, None)
        self._pending_events.pop(code, None)

    async def notify_pair_approved(self, code: str, device_id: str, device_secret: str) -> bool:
        ws = self._pending_pairs.pop(code, None)
        evt = self._pending_events.pop(code, None)
        if ws:
            try:
                await ws.send_text(json.dumps({
                    "type": "pair_success",
                    "protocol_version": "1.0.0",
                    "payload": {
                        "device_id": device_id,
                        "device_secret": device_secret,
                    },
                }))
                logger.info("Sent pair_success for code %s (device_id: %s)", code, device_id)
                if evt:
                    evt.set()
                return True
            except Exception as exc:
                logger.warning("Failed to send pair_success for code %s: %s", code, exc)
        if evt:
            evt.set()
        return False

    async def notify_pair_rejected(self, code: str, reason: str = "Pairing rejected") -> bool:
        ws = self._pending_pairs.pop(code, None)
        evt = self._pending_events.pop(code, None)
        if ws:
            try:
                await ws.send_text(json.dumps({
                    "type": "pair_rejected",
                    "protocol_version": "1.0.0",
                    "reason": reason,
                }))
                await ws.close()
                logger.info("Sent pair_rejected for code %s", code)
                if evt:
                    evt.set()
                return True
            except Exception as exc:
                logger.warning("Failed to send pair_rejected for code %s: %s", code, exc)
        if evt:
            evt.set()
        return False

    # ------------------------------------------------------------------
    # Agent management
    # ------------------------------------------------------------------

    async def register_agent(self, device_id: str, ws: WebSocket) -> AgentConnection:
        async with self._lock:
            # Evict stale connection if any
            if device_id in self._agents:
                logger.info("Replacing existing agent connection for %s", device_id)
                try:
                    await self._agents[device_id].ws.close()
                except Exception:
                    pass
            conn = AgentConnection(device_id, ws)
            self._agents[device_id] = conn
            logger.info("Agent registered: %s", device_id)
            return conn

    async def unregister_agent(self, device_id: str):
        async with self._lock:
            self._agents.pop(device_id, None)
            logger.info("Agent unregistered: %s", device_id)

    def get_agent(self, device_id: str) -> Optional[AgentConnection]:
        return self._agents.get(device_id)

    def agent_online(self, device_id: str) -> bool:
        return device_id in self._agents

    def online_device_ids(self) -> Set[str]:
        return set(self._agents.keys())

    async def send_to_agent(self, device_id: str, data: dict) -> bool:
        conn = self._agents.get(device_id)
        if conn is None:
            return False
        await conn.send(data)
        return True

    # ------------------------------------------------------------------
    # Controller management
    # ------------------------------------------------------------------

    async def register_controller(self, conn_id: str, ws: WebSocket) -> ControllerConnection:
        async with self._lock:
            conn = ControllerConnection(conn_id, ws)
            self._controllers[conn_id] = conn
            logger.info("Controller connected: %s", conn_id)
            return conn

    async def unregister_controller(self, conn_id: str):
        async with self._lock:
            self._controllers.pop(conn_id, None)
            logger.info("Controller disconnected: %s", conn_id)

    # ------------------------------------------------------------------
    # Broadcast
    # ------------------------------------------------------------------

    async def broadcast_to_controllers(self, data: dict):
        """Send a message to all connected controllers."""
        dead: list[str] = []
        for conn_id, conn in list(self._controllers.items()):
            try:
                await conn.send(data)
            except Exception:
                dead.append(conn_id)
        for conn_id in dead:
            await self.unregister_controller(conn_id)

    async def broadcast_to_all(self, data: dict):
        """Send a message to every connected client."""
        await self.broadcast_to_controllers(data)
        for conn in list(self._agents.values()):
            await conn.send(data)

    # ------------------------------------------------------------------
    # Heartbeat monitoring
    # ------------------------------------------------------------------

    def update_heartbeat(self, device_id: str):
        conn = self._agents.get(device_id)
        if conn:
            conn.last_heartbeat = time.time()

    def stale_agents(self) -> list[str]:
        threshold = time.time() - settings.heartbeat_timeout_seconds
        return [
            did for did, conn in self._agents.items()
            if conn.last_heartbeat < threshold
        ]


# Singleton shared across the application
manager = ConnectionManager()
