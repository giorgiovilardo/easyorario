"""Tests for health check endpoint."""

from unittest.mock import AsyncMock, patch


async def test_get_health_returns_200_with_ok_status(client):
    """GET /health returns 200 with {"status": "ok"}."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_get_health_returns_503_when_db_unreachable(client):
    """GET /health returns 503 when database is unreachable."""
    with patch(
        "easyorario.controllers.health.AsyncSession.execute",
        new_callable=AsyncMock,
        side_effect=ConnectionError("DB down"),
    ):
        response = await client.get("/health")
        assert response.status_code == 503
