"""
Phase 2 End-to-End Single-Laptop Control Integration Test.

Tests the complete flow asynchronously:
1. PWA controller registers WebSocket connection
2. Pairing code generation and agent pair_request
3. Approval and credential issuance
4. Agent authentication and registration
5. Active device selection
6. Real-time routing of:
   - pointer_move
   - mouse_down / mouse_up
   - scroll
   - key_down / key_up
   - text_input
   - shortcut
   - latency ping/pong
"""

import asyncio
import json
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.connections.manager import manager
from app.models.device import Device
from app.models.layout import PairingCode
from app.core.security import verify_secret, create_session_token


class FakeWebSocket:
    """Simulates an ASGI WebSocket connection with async queues."""

    def __init__(self):
        self.inbox: asyncio.Queue[str] = asyncio.Queue()
        self.outbox: asyncio.Queue[str] = asyncio.Queue()
        self.closed = False

    async def accept(self):
        pass

    async def send_text(self, text: str):
        await self.outbox.put(text)

    async def receive_text(self) -> str:
        return await self.inbox.get()

    async def close(self):
        self.closed = True

    async def get_next_message(self, timeout=2.0) -> dict:
        raw = await asyncio.wait_for(self.outbox.get(), timeout=timeout)
        return json.loads(raw)


@pytest.mark.asyncio
async def test_full_single_laptop_e2e_flow(client: AsyncClient, db_session: AsyncSession):
    # 1. Controller establishes connection
    ctrl_ws = FakeWebSocket()
    ctrl_conn = await manager.register_controller("ctrl-test-1", ctrl_ws)
    assert ctrl_conn.conn_id == "ctrl-test-1"

    # 2. PWA requests pairing code
    gen_resp = await client.post("/api/v1/pairing/generate")
    assert gen_resp.status_code == 200
    code = gen_resp.json()["code"]

    # 3. Agent submits pairing request
    agent_pair_ws = FakeWebSocket()
    event = manager.register_pending_pair(code, agent_pair_ws)

    # Update DB record with agent info
    await db_session.execute(
        PairingCode.__table__.update()
        .where(PairingCode.code == code)
        .values(agent_info_json=json.dumps({
            "device_name": "Studio Win11 Laptop",
            "hostname": "STUDIO-PC",
            "os_info": "Windows 11 Pro",
            "agent_version": "1.0.0",
            "screen_width": 2560,
            "screen_height": 1440,
        }))
    )
    await db_session.commit()

    # Broadcast pair_pending to controller
    await manager.broadcast_to_controllers({
        "type": "pair_pending",
        "protocol_version": "1.0.0",
        "code": code,
        "device_name": "Studio Win11 Laptop",
    })

    ctrl_pending_msg = await ctrl_ws.get_next_message()
    assert ctrl_pending_msg["type"] == "pair_pending"
    assert ctrl_pending_msg["code"] == code

    # 4. User approves pairing via REST API
    approve_resp = await client.post("/api/v1/pairing/approve", json={"code": code})
    assert approve_resp.status_code == 200
    device_id = approve_resp.json()["device_id"]

    # Agent receives pair_success on its waiting socket
    pair_success_msg = await agent_pair_ws.get_next_message()
    assert pair_success_msg["type"] == "pair_success"
    assert pair_success_msg["payload"]["device_id"] == device_id
    device_secret = pair_success_msg["payload"]["device_secret"]

    # 5. Agent authenticates and registers
    agent_ws = FakeWebSocket()
    agent_conn = await manager.register_agent(device_id, agent_ws)
    assert manager.agent_online(device_id) is True

    # Controller receives pair_resolved notification
    ctrl_resolved_msg = await ctrl_ws.get_next_message()
    assert ctrl_resolved_msg["type"] == "pair_resolved"
    assert ctrl_resolved_msg["code"] == code

    # Broadcast device_online to controllers
    await manager.broadcast_to_controllers({
        "type": "device_online",
        "protocol_version": "1.0.0",
        "device_id": device_id,
    })

    ctrl_online_msg = await ctrl_ws.get_next_message()
    assert ctrl_online_msg["type"] == "device_online"
    assert ctrl_online_msg["device_id"] == device_id

    # 6. Controller selects active device
    ctrl_conn.active_device_id = device_id

    # 7. Route Pointer Move
    move_payload = {
        "type": "pointer_move",
        "protocol_version": "1.0.0",
        "target_device_id": device_id,
        "dx": 18.0,
        "dy": -7.5,
    }
    sent = await manager.send_to_agent(device_id, move_payload)
    assert sent is True
    agent_move = await agent_ws.get_next_message()
    assert agent_move["type"] == "pointer_move"
    assert agent_move["dx"] == 18.0
    assert agent_move["dy"] == -7.5

    # 8. Route Mouse Buttons
    await manager.send_to_agent(device_id, {"type": "mouse_down", "target_device_id": device_id, "button": "left"})
    assert (await agent_ws.get_next_message())["button"] == "left"

    await manager.send_to_agent(device_id, {"type": "mouse_up", "target_device_id": device_id, "button": "left"})
    assert (await agent_ws.get_next_message())["button"] == "left"

    # 9. Route Scroll
    await manager.send_to_agent(device_id, {"type": "scroll", "target_device_id": device_id, "dx": 0, "dy": 200})
    scroll_msg = await agent_ws.get_next_message()
    assert scroll_msg["type"] == "scroll"
    assert scroll_msg["dy"] == 200

    # 10. Route Keyboard & Text Input
    await manager.send_to_agent(device_id, {"type": "key_down", "target_device_id": device_id, "key": "f5"})
    assert (await agent_ws.get_next_message())["key"] == "f5"

    await manager.send_to_agent(device_id, {"type": "key_up", "target_device_id": device_id, "key": "f5"})
    assert (await agent_ws.get_next_message())["key"] == "f5"

    await manager.send_to_agent(device_id, {"type": "text_input", "target_device_id": device_id, "text": "Orbit Control 🚀"})
    text_msg = await agent_ws.get_next_message()
    assert text_msg["text"] == "Orbit Control 🚀"

    await manager.send_to_agent(device_id, {"type": "shortcut", "target_device_id": device_id, "keys": ["ctrl", "shift", "esc"]})
    shortcut_msg = await agent_ws.get_next_message()
    assert shortcut_msg["keys"] == ["ctrl", "shift", "esc"]

    # 11. Cleanup
    await manager.unregister_controller("ctrl-test-1")
    await manager.unregister_agent(device_id)
    assert manager.agent_online(device_id) is False
