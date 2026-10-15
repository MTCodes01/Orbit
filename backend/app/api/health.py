"""Health check endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel
import time

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    timestamp: float
    version: str


@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="ok",
        timestamp=time.time(),
        version="1.0.0",
    )
