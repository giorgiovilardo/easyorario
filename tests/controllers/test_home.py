"""Tests for home page controller."""


async def test_get_index_returns_200_with_welcome_text(client):
    """GET / returns 200 with Italian welcome text."""
    response = await client.get("/")
    assert response.status_code == 200
    assert "Benvenuto su Easyorario" in response.text
