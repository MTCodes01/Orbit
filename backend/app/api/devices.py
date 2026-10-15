"""Device CRUD REST API."""

import json
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.engine import get_db
from app.models.device import Device
from app.connections.manager import manager

logger = logging.getLogger("orbit.api.devices")
router = APIRouter()


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class DeviceResponse(BaseModel):
    device_id: str
    friendly_name: str
    hostname: str
    os_info: str
    agent_version: str
    screen_width: int
    screen_height: int
    online: bool
    is_paired: bool
    last_seen_at: Optional[str]
    layout_x: Optional[float]
    layout_y: Optional[float]
    capabilities: dict

    model_config = {"from_attributes": True}


class RenameRequest(BaseModel):
    friendly_name: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _device_to_response(d: Device) -> DeviceResponse:
    return DeviceResponse(
        device_id=d.id,
        friendly_name=d.friendly_name,
        hostname=d.hostname,
        os_info=d.os_info,
        agent_version=d.agent_version,
        screen_width=d.screen_width,
        screen_height=d.screen_height,
        online=manager.agent_online(d.id),
        is_paired=d.is_paired,
        last_seen_at=d.last_seen_at.isoformat() if d.last_seen_at else None,
        layout_x=d.layout_x,
        layout_y=d.layout_y,
        capabilities=d.capabilities,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/", response_model=List[DeviceResponse])
async def list_devices(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Device).where(Device.is_paired == True))
    devices = result.scalars().all()
    return [_device_to_response(d) for d in devices]


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(device_id: str, db: AsyncSession = Depends(get_db)):
    device = await db.get(Device, device_id)
    if not device or not device.is_paired:
        raise HTTPException(status_code=404, detail="Device not found")
    return _device_to_response(device)


@router.patch("/{device_id}/rename", response_model=DeviceResponse)
async def rename_device(
    device_id: str,
    body: RenameRequest,
    db: AsyncSession = Depends(get_db),
):
    device = await db.get(Device, device_id)
    if not device or not device.is_paired:
        raise HTTPException(status_code=404, detail="Device not found")
    device.friendly_name = body.friendly_name.strip()[:128]
    await db.commit()
    await db.refresh(device)

    # Notify controllers of the name change
    await manager.broadcast_to_controllers({
        "type": "device_info",
        "device_id": device_id,
        "friendly_name": device.friendly_name,
    })
    return _device_to_response(device)


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unpair_device(device_id: str, db: AsyncSession = Depends(get_db)):
    device = await db.get(Device, device_id)
    if not device or not device.is_paired:
        raise HTTPException(status_code=404, detail="Device not found")

    # Revoke: close active connection first
    agent = manager.get_agent(device_id)
    if agent:
        try:
            await agent.send({"type": "device_revoked", "device_id": device_id})
            await agent.ws.close()
        except Exception:
            pass
        await manager.unregister_agent(device_id)

    # Remove DB record
    await db.delete(device)
    await db.commit()

    await manager.broadcast_to_controllers({
        "type": "device_revoked",
        "device_id": device_id,
    })
