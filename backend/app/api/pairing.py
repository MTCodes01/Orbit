"""Pairing flow: generate codes, approve or reject pending pairs."""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    generate_pairing_code,
    generate_device_id,
    generate_device_secret,
    hash_secret,
)
from app.database.engine import get_db
from app.models.device import Device
from app.models.layout import PairingCode
from app.connections.manager import manager

logger = logging.getLogger("orbit.api.pairing")
router = APIRouter()


class GenerateCodeResponse(BaseModel):
    code: str
    expires_in_seconds: int


class PendingPairResponse(BaseModel):
    code: str
    device_name: str
    hostname: str
    os_info: str
    agent_version: str
    screen_width: int
    screen_height: int


class ApproveRequest(BaseModel):
    code: str


@router.post("/generate", response_model=GenerateCodeResponse)
async def generate_code(db: AsyncSession = Depends(get_db)):
    """Generate a new short-lived pairing code for the PWA to display."""
    # Clean up expired codes
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(PairingCode).where(PairingCode.expires_at < now)
    )
    for old in result.scalars().all():
        await db.delete(old)

    code = generate_pairing_code()
    expires_at = now + timedelta(seconds=settings.pairing_code_expire_seconds)

    pc = PairingCode(code=code, expires_at=expires_at)
    db.add(pc)
    await db.commit()

    return GenerateCodeResponse(
        code=code,
        expires_in_seconds=settings.pairing_code_expire_seconds,
    )


@router.get("/pending", response_model=list[PendingPairResponse])
async def list_pending(db: AsyncSession = Depends(get_db)):
    """List pairing codes that have received agent info but not been approved."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(PairingCode).where(
            PairingCode.used == False,
            PairingCode.expires_at > now,
        )
    )
    pending = []
    for pc in result.scalars().all():
        info = pc.agent_info
        if info:
            pending.append(PendingPairResponse(
                code=pc.code,
                device_name=info.get("device_name", "Unknown"),
                hostname=info.get("hostname", ""),
                os_info=info.get("os_info", ""),
                agent_version=info.get("agent_version", ""),
                screen_width=info.get("screen_width", 1920),
                screen_height=info.get("screen_height", 1080),
            ))
    return pending


@router.post("/approve")
async def approve_pairing(body: ApproveRequest, db: AsyncSession = Depends(get_db)):
    """Approve a pending pairing code. Completes agent registration."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(PairingCode).where(
            PairingCode.code == body.code,
            PairingCode.used == False,
            PairingCode.expires_at > now,
        )
    )
    pc = result.scalar_one_or_none()
    if pc is None:
        raise HTTPException(status_code=404, detail="Pairing code not found or expired")

    agent_info = pc.agent_info
    if not agent_info:
        raise HTTPException(status_code=400, detail="Agent has not submitted pairing info yet")

    device_id = generate_device_id()
    raw_secret = generate_device_secret()
    secret_hash = hash_secret(raw_secret)

    device = Device(
        id=device_id,
        friendly_name=agent_info.get("device_name", "Orbit Laptop"),
        hostname=agent_info.get("hostname", "unknown"),
        os_info=agent_info.get("os_info", ""),
        agent_version=agent_info.get("agent_version", ""),
        screen_width=agent_info.get("screen_width", 1920),
        screen_height=agent_info.get("screen_height", 1080),
        device_secret_hash=secret_hash,
        is_paired=True,
    )
    db.add(device)

    pc.used = True
    await db.commit()

    # Notify the waiting agent directly via its WS connection
    await manager.notify_pair_approved(body.code, device_id, raw_secret)

    # Also broadcast to controllers to remove from pending
    await manager.broadcast_to_controllers({
        "type": "pair_resolved",
        "code": body.code,
        "status": "approved",
        "device_id": device_id,
    })

    return {"device_id": device_id, "status": "approved"}


@router.post("/reject")
async def reject_pairing(body: ApproveRequest, db: AsyncSession = Depends(get_db)):
    """Reject a pending pairing code."""
    result = await db.execute(
        select(PairingCode).where(PairingCode.code == body.code)
    )
    pc = result.scalar_one_or_none()
    if pc:
        pc.used = True
        await db.commit()
        await manager.notify_pair_rejected(body.code, "User rejected pairing")
        await manager.broadcast_to_controllers({
            "type": "pair_resolved",
            "code": body.code,
            "status": "rejected",
        })
    return {"status": "rejected"}
