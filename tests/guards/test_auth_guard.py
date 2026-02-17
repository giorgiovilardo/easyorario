"""Tests for auth guards."""

from unittest.mock import MagicMock

import pytest

from easyorario.guards.auth import requires_login, requires_role


def test_requires_login_raises_when_user_is_none():
    """requires_login raises NotAuthorizedException when connection.user is None."""
    from litestar.exceptions import NotAuthorizedException

    connection = MagicMock()
    connection.user = None
    handler = MagicMock()

    with pytest.raises(NotAuthorizedException):
        requires_login(connection, handler)


def test_requires_login_passes_when_user_exists():
    """requires_login does not raise when connection.user is set."""
    connection = MagicMock()
    connection.user = MagicMock()  # non-None user
    handler = MagicMock()

    requires_login(connection, handler)  # should not raise


def test_requires_role_raises_when_role_does_not_match():
    """requires_role raises NotAuthorizedException when user role doesn't match."""
    from litestar.exceptions import NotAuthorizedException

    connection = MagicMock()
    connection.user = MagicMock()
    connection.user.role = "responsible_professor"
    handler = MagicMock()
    handler.opt = {"required_role": "admin"}

    with pytest.raises(NotAuthorizedException):
        requires_role(connection, handler)


def test_requires_role_passes_when_role_matches():
    """requires_role does not raise when user role matches."""
    connection = MagicMock()
    connection.user = MagicMock()
    connection.user.role = "admin"
    handler = MagicMock()
    handler.opt = {"required_role": "admin"}

    requires_role(connection, handler)  # should not raise


def test_requires_role_raises_when_no_required_role_in_opt():
    """requires_role raises ImproperlyConfiguredException when required_role is missing."""
    from litestar.exceptions import ImproperlyConfiguredException

    connection = MagicMock()
    connection.user = MagicMock()
    handler = MagicMock()
    handler.opt = {}

    with pytest.raises(ImproperlyConfiguredException):
        requires_role(connection, handler)


# Integration tests: guard behavior via SessionAuth + exception handler

async def test_unauthenticated_request_to_protected_route_redirects_to_accedi(client):
    """Unauthenticated request to /dashboard redirects to /accedi."""
    response = await client.get("/dashboard", follow_redirects=False)
    assert response.status_code in (301, 302, 303)
    assert "/accedi" in response.headers.get("location", "")


async def test_authenticated_request_to_protected_route_succeeds(client):
    """Authenticated user can access /dashboard."""
    await client.get("/registrati")
    csrf = client.cookies.get("csrftoken", "")
    await client.post(
        "/registrati",
        data={"email": "guard@example.com", "password": "password123", "password_confirm": "password123"},
        headers={"x-csrftoken": csrf},
    )
    await client.get("/accedi")
    csrf = client.cookies.get("csrftoken", "")
    await client.post(
        "/accedi",
        data={"email": "guard@example.com", "password": "password123"},
        headers={"x-csrftoken": csrf},
        follow_redirects=False,
    )
    response = await client.get("/dashboard")
    assert response.status_code == 200
