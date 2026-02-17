"""Tests for dashboard controller."""


async def test_get_dashboard_as_responsible_professor_returns_200_with_nuovo_orario_button(
    authenticated_client,
):
    """AC #1: Responsible Professor sees dashboard with 'Nuovo Orario' button."""
    response = await authenticated_client.get("/dashboard")
    assert response.status_code == 200
    assert "Nuovo Orario" in response.text
    assert "Benvenuto" in response.text


async def test_get_dashboard_as_professor_returns_200_without_nuovo_orario_button(
    authenticated_professor_client,
):
    """AC #2: Professor sees dashboard WITHOUT 'Nuovo Orario' button."""
    response = await authenticated_professor_client.get("/dashboard")
    assert response.status_code == 200
    assert "Nuovo Orario" not in response.text


async def test_get_dashboard_as_professor_shows_shared_timetables_empty_state(
    authenticated_professor_client,
):
    """AC #2: Professor sees 'Nessun orario condiviso ancora' empty state."""
    response = await authenticated_professor_client.get("/dashboard")
    assert response.status_code == 200
    assert "Nessun orario condiviso ancora" in response.text


async def test_get_dashboard_unauthenticated_redirects_to_accedi(client):
    """AC #4: Unauthenticated access to /dashboard redirects to /accedi."""
    response = await client.get("/dashboard", follow_redirects=False)
    assert response.status_code in (301, 302, 303)
    assert "/accedi" in response.headers.get("location", "")
