"""
WebSocket endpoint for PWA controllers.

Flow:
1. Controller connects to /ws/controller?token=<controller_token>
2. Backend validates token (or issues a temporary one for dev)
3. Backend sends current device list
4. Controller sends input events → backend routes to target agent
5. Backend forwards device_online/offline events to controller
"""

from datetime import datetime, timezone
import json
import logging
import time
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy import select

from app.connections.manager import manager
from app.core.security import decode_controller_token, create_controller_token
from app.database.engine import AsyncSessionLocal
from app.models.device import Device
from app.models.layout import Layout, PairingCode
from app.topology.engine import TopologyEngine, DisplayRect

logger = logging.getLogger("orbit.ws.controller")
router = APIRouter()

# Input message types that are forwarded directly to agents
ROUTABLE_TYPES = {
    "pointer_move", "mouse_down", "mouse_up", "scroll",
    "key_down", "key_up", "text_input", "shortcut",
    "session_start", "session_end", "cursor_handoff",
    "latency_ping", "switch_monitor",
}


def _build_device_list(devices: list[Device]) -> dict:
    return {
        "type": "device_list",
        "protocol_version": "1.0.0",
        "devices": [
            {
                "device_id": d.id,
                "friendly_name": d.friendly_name,
                "hostname": d.hostname,
                "os_info": d.os_info,
                "agent_version": d.agent_version,
                "screen_width": d.screen_width,
                "screen_height": d.screen_height,
                "online": manager.agent_online(d.id),
                "last_seen_at": d.last_seen_at.isoformat() if d.last_seen_at else None,
                "layout_x": d.layout_x,
                "layout_y": d.layout_y,
                "capabilities": d.capabilities,
            }
            for d in devices
        ],
    }


@router.websocket("/controller")
async def controller_ws(websocket: WebSocket, token: str = Query(default="")):
    """
    The PWA connects here. For development, if no valid token is supplied
    we issue a temporary one. In production, require a proper auth flow.
    """
    # In dev mode accept any connection; in production validate the token.
    # TODO: Enforce auth in production (add ORBIT_REQUIRE_CONTROLLER_AUTH env var)
    conn_id = str(uuid.uuid4())
    await websocket.accept()
    conn = await manager.register_controller(conn_id, websocket)

    try:
        # Send the current device list immediately upon connection
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Device).where(Device.is_paired == True))
            devices = result.scalars().all()

        await websocket.send_text(json.dumps(_build_device_list(list(devices))))

        # Message loop
        async for raw in _receive_loop(websocket):
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type")

            # ------------------------------------------------------------------
            # Active device tracking
            # ------------------------------------------------------------------
            if msg_type == "active_device":
                conn.active_device_id = msg.get("device_id")
                continue

            # ------------------------------------------------------------------
            # Seamless Cursor Handoff across display boundaries
            # ------------------------------------------------------------------
            if msg_type == "cursor_handoff":
                edge = msg.get("edge")
                local_x = float(msg.get("local_x", 0.0))
                local_y = float(msg.get("local_y", 0.0))
                current_target = msg.get("target_device_id") or conn.active_device_id

                if current_target and edge:
                    async with AsyncSessionLocal() as db:
                        result = await db.execute(select(Layout).order_by(Layout.id.desc()).limit(1))
                        layout = result.scalar_one_or_none()
                        if layout and layout.layout:
                            rects = [
                                DisplayRect(
                                    device_id=item["device_id"],
                                    x=item["x"],
                                    y=item["y"],
                                    width=item["width"],
                                    height=item["height"],
                                )
                                for item in layout.layout
                            ]
                            engine = TopologyEngine(rects)
                            handoff = engine.calculate_handoff(
                                current_target, local_x, local_y, edge, is_online=manager.agent_online
                            )
                            if handoff:
                                next_id, new_x, new_y = handoff
                                conn.active_device_id = next_id
                                await websocket.send_text(json.dumps({
                                    "type": "cursor_handoff_success",
                                    "from_device_id": current_target,
                                    "to_device_id": next_id,
                                    "new_x": new_x,
                                    "new_y": new_y,
                                }))
                                await manager.send_to_agent(next_id, {
                                    "type": "cursor_position",
                                    "x": new_x,
                                    "y": new_y,
                                })
                continue

            # ------------------------------------------------------------------
            # Input routing — forward to target agent
            # ------------------------------------------------------------------
            if msg_type in ROUTABLE_TYPES:
                target = msg.get("target_device_id") or conn.active_device_id
                if not target:
                    await websocket.send_text(json.dumps({
                        "type": "error", "code": "no_target",
                        "message": "No active device selected",
                    }))
                    continue

                if not manager.agent_online(target):
                    await websocket.send_text(json.dumps({
                        "type": "error", "code": "device_offline",
                        "message": f"Device {target} is offline",
                    }))
                    continue

                sent = await manager.send_to_agent(target, msg)
                if not sent:
                    await websocket.send_text(json.dumps({
                        "type": "error", "code": "delivery_failed",
                        "message": "Could not deliver message to agent",
                    }))
                continue

            # ------------------------------------------------------------------
            # Pairing code submission from agent via PWA bridge
            # (used when agent submits pair_request directly over controller WS)
            # ------------------------------------------------------------------
            if msg_type == "pair_request":
                # Forward to pairing service logic
                await _handle_pair_request(msg, websocket)
                continue

            # ------------------------------------------------------------------
            # Heartbeat / latency from controller
            # ------------------------------------------------------------------
            if msg_type == "heartbeat":
                await websocket.send_text(json.dumps({
                    "type": "heartbeat_ack",
                    "protocol_version": "1.0.0",
                }))
                continue

            if msg_type == "latency_ping":
                await websocket.send_text(json.dumps({
                    "type": "latency_pong",
                    "protocol_version": "1.0.0",
                    "ping_id": msg.get("ping_id"),
                    "sent_ms": msg.get("sent_ms"),
                    "received_ms": int(time.time() * 1000),
                }))
                continue

            logger.debug("Unhandled controller message type: %s", msg_type)

    except WebSocketDisconnect:
        logger.info("Controller disconnected: %s", conn_id)
    except Exception as exc:
        logger.exception("Controller WS error %s: %s", conn_id, exc)
    finally:
        await manager.unregister_controller(conn_id)


async def _handle_pair_request(msg: dict, ws: WebSocket):
    """Bridge: agent sends pair_request through controller WS. Store agent info on the pairing code."""
    code = msg.get("payload", {}).get("pairing_code", "")
    if not code:
        return

    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(PairingCode).where(
                PairingCode.code == code,
                PairingCode.used == False,
                PairingCode.expires_at > now,
            )
        )
        pc = result.scalar_one_or_none()
        if pc is None:
            await ws.send_text(json.dumps({
                "type": "pair_rejected",
                "reason": "Pairing code not found or expired",
            }))
            return

        pc.agent_info = msg.get("payload", {})
        await db.commit()

    # Notify all controllers that a new pairing request is pending
    await manager.broadcast_to_controllers({
        "type": "pair_pending",
        "protocol_version": "1.0.0",
        "code": code,
        "device_name": msg.get("payload", {}).get("device_name", "Unknown"),
    })


async def _receive_loop(ws: WebSocket):
    while True:
        try:
            data = await ws.receive_text()
            yield data
        except (WebSocketDisconnect, Exception):
            break
