"""
WebSocket endpoint for Windows agents.

Flow:
1. Agent connects to /ws/agent
2. Agent sends auth_request { device_id, device_secret }
3. Backend validates credentials, sends auth_success { session_token }
4. Agent sends device_register with full metadata
5. Backend marks device online, notifies controllers
6. Bidirectional: heartbeats, topology updates, input routing acks
"""

import json
import logging
import time
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.connections.manager import manager
from app.core.security import verify_secret, create_session_token
from app.database.engine import AsyncSessionLocal
from app.models.device import Device

logger = logging.getLogger("orbit.ws.agent")
router = APIRouter()


async def _get_device(db: AsyncSession, device_id: str) -> Device | None:
    return await db.get(Device, device_id)


@router.websocket("/agent")
async def agent_ws(websocket: WebSocket):
    await websocket.accept()
    device_id: str | None = None

    try:
        # ------------------------------------------------------------------
        # Step 1: Wait for auth_request
        # ------------------------------------------------------------------
        raw = await websocket.receive_text()
        msg = json.loads(raw)

        if msg.get("type") == "pair_request":
            payload = msg.get("payload", {})
            code = payload.get("pairing_code", "")
            if not code:
                await websocket.send_text(json.dumps({
                    "type": "error", "code": "missing_code", "message": "pairing_code is required"
                }))
                await websocket.close()
                return

            from app.models.layout import PairingCode
            from sqlalchemy import select
            now = datetime.now(timezone.utc)
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(PairingCode).where(
                        PairingCode.code == code,
                        PairingCode.used == False,
                        PairingCode.expires_at > now,
                    )
                )
                pc = result.scalar_one_or_none()
                if pc is None:
                    await websocket.send_text(json.dumps({
                        "type": "pair_rejected",
                        "protocol_version": "1.0.0",
                        "reason": "Pairing code not found or expired",
                    }))
                    await websocket.close()
                    return

                pc.agent_info = payload
                await db.commit()

            # Register this websocket for the pending pair
            event = manager.register_pending_pair(code, websocket)

            # Broadcast to all controllers that an agent submitted a pairing code
            await manager.broadcast_to_controllers({
                "type": "pair_pending",
                "protocol_version": "1.0.0",
                "code": code,
                "device_name": payload.get("device_name", "Unknown"),
            })

            # Wait for approve/reject resolution
            try:
                await event.wait()
            except (WebSocketDisconnect, Exception):
                pass
            finally:
                manager.unregister_pending_pair(code)
            return

        if msg.get("type") != "auth_request":
            await websocket.send_text(json.dumps({
                "type": "error", "code": "unauthorized",
                "message": "Expected auth_request or pair_request as first message",
            }))
            await websocket.close()
            return

        payload = msg.get("payload", {})
        device_id = payload.get("device_id", "")
        device_secret = payload.get("device_secret", "")

        async with AsyncSessionLocal() as db:
            device = await _get_device(db, device_id)
            if not device or not device.is_paired:
                await websocket.send_text(json.dumps({
                    "type": "auth_failed",
                    "reason": "Device not found or not paired",
                }))
                await websocket.close()
                return

            if not verify_secret(device_secret, device.device_secret_hash or ""):
                await websocket.send_text(json.dumps({
                    "type": "auth_failed",
                    "reason": "Invalid credentials",
                }))
                await websocket.close()
                return

        session_token = create_session_token(device_id)
        await websocket.send_text(json.dumps({
            "type": "auth_success",
            "protocol_version": "1.0.0",
            "session_token": session_token,
        }))

        # ------------------------------------------------------------------
        # Step 2: Register the agent connection
        # ------------------------------------------------------------------
        conn = await manager.register_agent(device_id, websocket)

        # ------------------------------------------------------------------
        # Step 3: Wait for device_register, then mark online
        # ------------------------------------------------------------------
        raw = await websocket.receive_text()
        msg = json.loads(raw)

        if msg.get("type") == "device_register":
            payload = msg.get("payload", {})
            async with AsyncSessionLocal() as db:
                device = await _get_device(db, device_id)
                if device:
                    device.friendly_name = payload.get("friendly_name", device.friendly_name)
                    device.hostname = payload.get("hostname", device.hostname)
                    device.os_info = payload.get("os_info", device.os_info)
                    device.agent_version = payload.get("agent_version", device.agent_version)
                    device.screen_width = payload.get("screen_width", device.screen_width)
                    device.screen_height = payload.get("screen_height", device.screen_height)
                    device.capabilities = payload.get("capabilities", {})
                    device.online = True
                    device.touch()
                    await db.commit()

        # Notify controllers
        await manager.broadcast_to_controllers({
            "type": "device_online",
            "protocol_version": "1.0.0",
            "device_id": device_id,
        })

        logger.info("Agent fully connected: %s", device_id)

        # ------------------------------------------------------------------
        # Step 4: Message loop
        # ------------------------------------------------------------------
        async for raw in _receive_loop(websocket):
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type")

            if msg_type == "heartbeat":
                manager.update_heartbeat(device_id)
                await websocket.send_text(json.dumps({
                    "type": "heartbeat_ack",
                    "protocol_version": "1.0.0",
                }))
                # Update last_seen
                async with AsyncSessionLocal() as db:
                    device = await _get_device(db, device_id)
                    if device:
                        device.touch()
                        await db.commit()

            elif msg_type == "latency_pong":
                # Echo back for RTT measurement
                pass

            elif msg_type == "diagnostic":
                logger.debug("Agent diagnostic [%s]: %s", device_id, msg)

            else:
                logger.debug("Unhandled agent message type: %s", msg_type)

    except WebSocketDisconnect:
        logger.info("Agent disconnected: %s", device_id)
    except Exception as exc:
        logger.exception("Agent WS error for %s: %s", device_id, exc)
    finally:
        if device_id:
            await manager.unregister_agent(device_id)
            async with AsyncSessionLocal() as db:
                device = await _get_device(db, device_id)
                if device:
                    device.online = False
                    await db.commit()
            await manager.broadcast_to_controllers({
                "type": "device_offline",
                "protocol_version": "1.0.0",
                "device_id": device_id,
            })


async def _receive_loop(ws: WebSocket):
    """Async generator that yields raw text messages."""
    while True:
        try:
            data = await ws.receive_text()
            yield data
        except WebSocketDisconnect:
            break
        except Exception:
            break
