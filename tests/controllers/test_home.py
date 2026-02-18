"""Tests for home page controller."""


async def test_get_home_unauthenticated_renders_index(client):
    """AC #5: GET / when not authenticated renders the landing page."""
    response = await client.get("/")
    assert response.status_code == 200
    assert "Crea orari scolastici senza stress" in response.text


async def test_get_home_authenticated_redirects_to_dashboard(authenticated_client):
    """AC #5: GET / when authenticated redirects to /dashboard."""
    response = await authenticated_client.get("/", follow_redirects=False)
    assert response.status_code in (301, 302, 303)
    assert response.headers.get("location") == "/dashboard"
