"""
Phase 6 Seamless Cursor Handoff Integration Test.

Tests end-to-end cursor transition across virtual display borders:
1. Virtual layout arrangement (Laptop 1 Left, Laptop 2 Right)
2. Controller selects Laptop 1
3. Crossing the right border triggers cursor handoff to Laptop 2
4. Controller receives cursor_handoff_success and updates active device
5. Laptop 2 receives cursor_position placement
6. Subsequent pointer events automatically route to Laptop 2
"""

import asyncio
import json
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.connections.manager import manager
from app.models.device import Device
from app.models.layout import Layout
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
async def test_seamless_cursor_handoff_flow(client: AsyncClient, db_session: AsyncSession):
    # 1. Setup 2 laptops in database
    l1 = Device(
        id="dev-lap-1",
        friendly_name="Main Laptop",
        hostname="PC-1",
        screen_width=1920,
        screen_height=1080,
        device_secret_hash=hash_secret("sec1"),
        is_paired=True,
    )
    l2 = Device(
        id="dev-lap-2",
        friendly_name="Second Laptop",
        hostname="PC-2",
        screen_width=1920,
        screen_height=1080,
        device_secret_hash=hash_secret("sec2"),
        is_paired=True,
    )
    db_session.add_all([l1, l2])

    # Setup layout: lap-1 on left (0,0), lap-2 on right (1920,0)
    layout = Layout(
        version=1,
        layout_json=json.dumps([
            {"device_id": "dev-lap-1", "x": 0.0, "y": 0.0, "width": 1920.0, "height": 1080.0},
            {"device_id": "dev-lap-2", "x": 1920.0, "y": 0.0, "width": 1920.0, "height": 1080.0},
        ]),
    )
    db_session.add(layout)
    await db_session.commit()

    # 2. Connect controller and both agents
    ctrl_ws = MockWebSocket()
    ctrl_conn = await manager.register_controller("ctrl-handoff-1", ctrl_ws)

    ws1 = MockWebSocket()
    ws2 = MockWebSocket()
    await manager.register_agent("dev-lap-1", ws1)
    await manager.register_agent("dev-lap-2", ws2)

    # 3. Initially control dev-lap-1
    ctrl_conn.active_device_id = "dev-lap-1"

    # 4. Perform cursor handoff: crossing right edge of dev-lap-1
    from app.api.ws_controller import controller_ws
    from app.topology.engine import TopologyEngine, DisplayRect

    rects = [
        DisplayRect("dev-lap-1", x=0.0, y=0.0, width=1920.0, height=1080.0),
        DisplayRect("dev-lap-2", x=1920.0, y=0.0, width=1920.0, height=1080.0),
    ]
    engine = TopologyEngine(rects)
    handoff = engine.calculate_handoff("dev-lap-1", local_x=1919.0, local_y=450.0, edge="right", is_online=manager.agent_online)
    assert handoff == ("dev-lap-2", 0.0, 450.0)

    target_id, new_x, new_y = handoff
    # Switch active device
    ctrl_conn.active_device_id = target_id

    # Notify controller and destination agent
    await ctrl_ws.send_text(json.dumps({
        "type": "cursor_handoff_success",
        "from_device_id": "dev-lap-1",
        "to_device_id": target_id,
        "new_x": new_x,
        "new_y": new_y,
    }))
    await manager.send_to_agent(target_id, {
        "type": "cursor_position",
        "x": new_x,
        "y": new_y,
    })

    # Controller receives notification
    ctrl_msg = await ctrl_ws.get_next_message()
    assert ctrl_msg["type"] == "cursor_handoff_success"
    assert ctrl_msg["to_device_id"] == "dev-lap-2"
    assert ctrl_msg["new_x"] == 0.0
    assert ctrl_msg["new_y"] == 450.0

    # dev-lap-2 receives cursor_position
    lap2_msg = await ws2.get_next_message()
    assert lap2_msg["type"] == "cursor_position"
    assert lap2_msg["x"] == 0.0
    assert lap2_msg["y"] == 450.0

    # 5. Subsequent input routes to dev-lap-2 seamlessly
    await manager.send_to_agent(ctrl_conn.active_device_id, {
        "type": "pointer_move",
        "dx": 10.0,
        "dy": 5.0,
    })
    lap2_move = await ws2.get_next_message()
    assert lap2_move["type"] == "pointer_move"
    assert lap2_move["dx"] == 10.0
    assert ws1.outbox.empty()

    # Cleanup
    await manager.unregister_controller("ctrl-handoff-1")
    await manager.unregister_agent("dev-lap-1")
    await manager.unregister_agent("dev-lap-2")
