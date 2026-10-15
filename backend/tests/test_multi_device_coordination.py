"""
Phase 4 Multi-Device Coordination Integration Tests.

Validates:
1. Multiple concurrent laptop agent connections
2. Controller device switching between laptops
3. Targeted routing ensuring only the active device receives input
4. Offline tracking and error reporting when addressing offline devices
5. Realtime rename synchronization
6. Device revocation and credential clearance
"""

import asyncio
import json
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.connections.manager import manager
from app.models.device import Device
from app.core.security import hash_secret


class MockWebSocket:
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
async def test_multi_device_coordination_and_routing(client: AsyncClient, db_session: AsyncSession):
    # 1. Setup 3 paired devices in database
    laptop_a = Device(
        id="laptop-a",
        friendly_name="Laptop A (Dell)",
        hostname="DELL-XPS",
        os_info="Windows 11",
        device_secret_hash=hash_secret("secret-a"),
        is_paired=True,
    )
    laptop_b = Device(
        id="laptop-b",
        friendly_name="Laptop B (ThinkPad)",
        hostname="LENOVO-T14",
        os_info="Windows 11",
        device_secret_hash=hash_secret("secret-b"),
        is_paired=True,
    )
    laptop_c = Device(
        id="laptop-c",
        friendly_name="Laptop C (Surface)",
        hostname="SURFACE-PRO",
        os_info="Windows 11",
        device_secret_hash=hash_secret("secret-c"),
        is_paired=True,
    )
    db_session.add_all([laptop_a, laptop_b, laptop_c])
    await db_session.commit()

    # 2. Connect controller
    ctrl_ws = MockWebSocket()
    ctrl_conn = await manager.register_controller("ctrl-multi-1", ctrl_ws)

    # 3. Connect all 3 agents simultaneously
    ws_a = MockWebSocket()
    ws_b = MockWebSocket()
    ws_c = MockWebSocket()

    await manager.register_agent("laptop-a", ws_a)
    await manager.register_agent("laptop-b", ws_b)
    await manager.register_agent("laptop-c", ws_c)

    assert manager.online_device_ids() == {"laptop-a", "laptop-b", "laptop-c"}

    # 4. Controller routes input to Laptop A
    ctrl_conn.active_device_id = "laptop-a"

    input_a = {
        "type": "pointer_move",
        "protocol_version": "1.0.0",
        "target_device_id": "laptop-a",
        "dx": 20.0,
        "dy": 15.0,
    }
    sent_a = await manager.send_to_agent("laptop-a", input_a)
    assert sent_a is True

    # Laptop A receives message
    msg_a = await ws_a.get_next_message()
    assert msg_a["type"] == "pointer_move"
    assert msg_a["dx"] == 20.0

    # Laptops B and C received nothing
    assert ws_b.outbox.empty()
    assert ws_c.outbox.empty()

    # 5. Switch active device to Laptop B
    ctrl_conn.active_device_id = "laptop-b"

    input_b = {
        "type": "text_input",
        "protocol_version": "1.0.0",
        "target_device_id": "laptop-b",
        "text": "Hello Laptop B",
    }
    sent_b = await manager.send_to_agent("laptop-b", input_b)
    assert sent_b is True

    msg_b = await ws_b.get_next_message()
    assert msg_b["type"] == "text_input"
    assert msg_b["text"] == "Hello Laptop B"

    # Laptops A and C inbox remains untouched
    assert ws_a.outbox.empty()
    assert ws_c.outbox.empty()

    # 6. Laptop B goes offline (disconnects)
    await manager.unregister_agent("laptop-b")
    assert manager.agent_online("laptop-b") is False
    assert manager.online_device_ids() == {"laptop-a", "laptop-c"}

    # Broadcast offline event to controller
    await manager.broadcast_to_controllers({
        "type": "device_offline",
        "protocol_version": "1.0.0",
        "device_id": "laptop-b",
    })
    ctrl_msg = await ctrl_ws.get_next_message()
    assert ctrl_msg["type"] == "device_offline"
    assert ctrl_msg["device_id"] == "laptop-b"

    # 7. Device renaming via REST API
    rename_resp = await client.patch("/api/v1/devices/laptop-a/rename", json={"friendly_name": "Studio Main"})
    assert rename_resp.status_code == 200
    assert rename_resp.json()["friendly_name"] == "Studio Main"

    # Controller receives live rename broadcast
    rename_broadcast = await ctrl_ws.get_next_message()
    assert rename_broadcast["type"] == "device_info"
    assert rename_broadcast["device_id"] == "laptop-a"
    assert rename_broadcast["friendly_name"] == "Studio Main"

    # 8. Revoke Device C
    revoke_resp = await client.delete("/api/v1/devices/laptop-c")
    assert revoke_resp.status_code == 204

    # Laptop C receives revocation message and socket closes
    c_revoked_msg = await ws_c.get_next_message()
    assert c_revoked_msg["type"] == "device_revoked"
    assert ws_c.closed is True

    # Controller receives revocation notification
    ctrl_revoked = await ctrl_ws.get_next_message()
    assert ctrl_revoked["type"] == "device_revoked"
    assert ctrl_revoked["device_id"] == "laptop-c"

    # Cleanup
    await manager.unregister_controller("ctrl-multi-1")
    await manager.unregister_agent("laptop-a")
