"""Tests for 401 redirect and 403 error page exception handlers."""


async def test_unauthenticated_access_to_protected_route_redirects_to_accedi(client):
    """AC #4: Unauthenticated request to a protected route redirects to /accedi."""
    response = await client.get("/dashboard", follow_redirects=False)
    assert response.status_code in (301, 302, 303)
    assert response.headers.get("location") == "/accedi"


async def test_unauthorized_role_returns_403_with_italian_message(authenticated_professor_client):
    """AC #3: Professor accessing RP-only route gets 403 with Italian error."""
    response = await authenticated_professor_client.get("/orario/nuovo")
    assert response.status_code == 403
    assert "Accesso negato" in response.text
    assert "permessi" in response.text
