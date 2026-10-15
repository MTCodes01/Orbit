"""Layout topology REST API."""

import json
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.engine import get_db
from app.models.layout import Layout
from app.models.device import Device
from app.connections.manager import manager

logger = logging.getLogger("orbit.api.layout")
router = APIRouter()


class LayoutDeviceItem(BaseModel):
    device_id: str
    x: float
    y: float
    width: float
    height: float


class LayoutUpdateRequest(BaseModel):
    layout: List[LayoutDeviceItem]


class LayoutResponse(BaseModel):
    version: int
    layout: List[LayoutDeviceItem]


async def _get_or_create_layout(db: AsyncSession) -> Layout:
    result = await db.execute(select(Layout).order_by(Layout.id.desc()).limit(1))
    layout = result.scalar_one_or_none()
    if layout is None:
        layout = Layout(version=1, layout_json="[]")
        db.add(layout)
        await db.commit()
        await db.refresh(layout)
    return layout


@router.get("/", response_model=LayoutResponse)
async def get_layout(db: AsyncSession = Depends(get_db)):
    layout = await _get_or_create_layout(db)
    return LayoutResponse(
        version=layout.version,
        layout=[LayoutDeviceItem(**item) for item in layout.layout],
    )


@router.put("/", response_model=LayoutResponse)
async def update_layout(body: LayoutUpdateRequest, db: AsyncSession = Depends(get_db)):
    """Replace the current layout with a new arrangement."""
    # Validate all device_ids exist
    for item in body.layout:
        device = await db.get(Device, item.device_id)
        if not device or not device.is_paired:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown device: {item.device_id}",
            )

    layout = await _get_or_create_layout(db)
    layout.version += 1
    layout.layout = [item.model_dump() for item in body.layout]

    # Update per-device layout positions
    for item in body.layout:
        device = await db.get(Device, item.device_id)
        if device:
            device.layout_x = item.x
            device.layout_y = item.y

    await db.commit()
    await db.refresh(layout)

    # Broadcast topology update to all connections
    await manager.broadcast_to_all({
        "type": "topology_update",
        "protocol_version": "1.0.0",
        "version": layout.version,
        "layout": [item.model_dump() for item in body.layout],
    })

    return LayoutResponse(
        version=layout.version,
        layout=body.layout,
    )
