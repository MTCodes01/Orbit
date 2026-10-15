"""Tests for device REST endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_list_devices_empty(client: AsyncClient):
    resp = await client.get("/api/v1/devices/")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_generate_pairing_code(client: AsyncClient):
    resp = await client.post("/api/v1/pairing/generate")
    assert resp.status_code == 200
    data = resp.json()
    assert "code" in data
    assert len(data["code"]) == 6
    assert data["code"].isdigit()
    assert data["expires_in_seconds"] == 120


@pytest.mark.asyncio
async def test_get_layout_empty(client: AsyncClient):
    resp = await client.get("/api/v1/layout/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == 1
    assert data["layout"] == []
