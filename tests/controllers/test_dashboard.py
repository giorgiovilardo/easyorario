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


async def test_dashboard_nav_shows_logout_button(authenticated_client):
    """AC #1, #2: Dashboard nav shows user email and 'Esci' logout button."""
    response = await authenticated_client.get("/dashboard")
    assert response.status_code == 200
    assert "Esci" in response.text
    assert 'action="/esci"' in response.text
    assert "test@example.com" in response.text


async def test_unauthenticated_page_nav_shows_login_register_links(client):
    """Unauthenticated pages show 'Accedi' and 'Registrati' links in nav."""
    response = await client.get("/")
    assert response.status_code == 200
    assert "Accedi" in response.text
    assert "Registrati" in response.text
