"""Integration tests for /api/v1/athletes endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport

from terratrain.main import app


@pytest.mark.asyncio
async def test_create_and_get_athlete():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "intervals_user_id": "test_user_001",
            "name": "Test Rider",
            "sport": "cycling",
            "ftp_watts": 300,
            "weight_kg": 72.0,
        }
        response = await client.post("/api/v1/athletes", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Rider"
        assert data["ftp_watts"] == 300

        athlete_id = data["id"]
        get_resp = await client.get(f"/api/v1/athletes/{athlete_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == athlete_id


@pytest.mark.asyncio
async def test_get_nonexistent_athlete_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/athletes/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404
