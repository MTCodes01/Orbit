"""Integration tests for device lifecycle, pairing flow, and virtual layout."""

from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.layout import PairingCode
from app.models.device import Device


@pytest.mark.asyncio
async def test_pairing_flow_reject(client: AsyncClient, db_session: AsyncSession):
    # 1. Generate code
    resp = await client.post("/api/v1/pairing/generate")
    assert resp.status_code == 200
    code = resp.json()["code"]

    # 2. Reject code
    resp = await client.post("/api/v1/pairing/reject", json={"code": code})
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"


@pytest.mark.asyncio
async def test_pairing_flow_approve_and_device_lifecycle(client: AsyncClient, db_session: AsyncSession):
    # 1. Generate pairing code
    resp = await client.post("/api/v1/pairing/generate")
    assert resp.status_code == 200
    code = resp.json()["code"]

    # Simulate agent submitting device info for this pairing code
    pc = (await db_session.execute(
        PairingCode.__table__.select().where(PairingCode.code == code)
    )).first()
    assert pc is not None

    # Update pairing code with agent info in db
    import json
    await db_session.execute(
        PairingCode.__table__.update()
        .where(PairingCode.code == code)
        .values(agent_info_json=json.dumps({
            "device_name": "Studio Laptop",
            "hostname": "STUDIO-WIN11",
            "os_info": "Windows 11",
            "agent_version": "1.0.0",
            "screen_width": 2560,
            "screen_height": 1440,
        }))
    )
    await db_session.commit()

    # 2. Check pending list
    resp = await client.get("/api/v1/pairing/pending")
    assert resp.status_code == 200
    pending = resp.json()
    assert len(pending) == 1
    assert pending[0]["code"] == code
    assert pending[0]["device_name"] == "Studio Laptop"

    # 3. Approve pairing
    resp = await client.post("/api/v1/pairing/approve", json={"code": code})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "approved"
    device_id = data["device_id"]

    # 4. Fetch device list
    resp = await client.get("/api/v1/devices/")
    assert resp.status_code == 200
    devices = resp.json()
    assert len(devices) == 1
    assert devices[0]["device_id"] == device_id
    assert devices[0]["friendly_name"] == "Studio Laptop"

    # 5. Fetch single device
    resp = await client.get(f"/api/v1/devices/{device_id}")
    assert resp.status_code == 200
    assert resp.json()["friendly_name"] == "Studio Laptop"

    # 6. Rename device
    resp = await client.patch(f"/api/v1/devices/{device_id}/rename", json={"friendly_name": "Main Workstation"})
    assert resp.status_code == 200
    assert resp.json()["friendly_name"] == "Main Workstation"

    # 7. Update layout
    layout_data = {
        "layout": [
            {
                "device_id": device_id,
                "x": 0.0,
                "y": 0.0,
                "width": 1920.0,
                "height": 1080.0,
            }
        ]
    }
    resp = await client.put("/api/v1/layout/", json=layout_data)
    assert resp.status_code == 200
    assert resp.json()["version"] >= 2
    assert len(resp.json()["layout"]) == 1

    # Verify get layout
    resp = await client.get("/api/v1/layout/")
    assert resp.status_code == 200
    assert len(resp.json()["layout"]) == 1
    assert resp.json()["layout"][0]["device_id"] == device_id

    # 8. Unpair device
    resp = await client.delete(f"/api/v1/devices/{device_id}")
    assert resp.status_code == 204

    # Verify device list is now empty
    resp = await client.get("/api/v1/devices/")
    assert resp.status_code == 200
    assert resp.json() == []
