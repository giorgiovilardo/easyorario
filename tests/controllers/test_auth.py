"""Tests for AuthController registration and login endpoints."""

import pytest

from easyorario.models.user import User
from easyorario.services.auth import hash_password


def _get_csrf_token(client) -> str:
    """Get CSRF token from the client's cookie jar."""
    token = client.cookies.get("csrftoken")
    if not token:
        raise AssertionError("No CSRF cookie found in client cookie jar")
    return token


async def test_get_registrati_returns_200_with_form(client):
    """GET /registrati returns 200 with the registration form."""
    response = await client.get("/registrati")
    assert response.status_code == 200
    assert "Registrati" in response.text
    assert 'name="email"' in response.text
    assert 'name="password"' in response.text


async def test_post_registrati_with_valid_data_redirects_to_accedi(client):
    """POST /registrati with valid data redirects to /accedi with success message."""
    await client.get("/registrati")
    csrf_token = _get_csrf_token(client)

    response = await client.post(
        "/registrati",
        data={"email": "new@example.com", "password": "validpass123", "password_confirm": "validpass123"},
        headers={"x-csrftoken": csrf_token},
    )
    # Client follows redirect; verify via history
    assert len(response.history) == 1
    redirect = response.history[0]
    assert redirect.status_code in (301, 302, 303)
    assert "/accedi" in redirect.headers.get("location", "")
    assert "msg=registration_success" in redirect.headers.get("location", "")


async def test_post_registrati_with_duplicate_email_shows_error(client):
    """POST /registrati with already-used email shows Italian error."""
    await client.get("/registrati")
    csrf_token = _get_csrf_token(client)

    # Register first time
    await client.post(
        "/registrati",
        data={"email": "dup@example.com", "password": "validpass123", "password_confirm": "validpass123"},
        headers={"x-csrftoken": csrf_token},
    )

    # Register again with same email
    response = await client.post(
        "/registrati",
        data={"email": "dup@example.com", "password": "validpass123", "password_confirm": "validpass123"},
        headers={"x-csrftoken": csrf_token},
    )
    assert response.status_code == 200
    assert "già registrato" in response.text


async def test_post_registrati_with_short_password_shows_error(client):
    """POST /registrati with password < 8 chars shows Italian error."""
    await client.get("/registrati")
    csrf_token = _get_csrf_token(client)

    response = await client.post(
        "/registrati",
        data={"email": "short@example.com", "password": "short", "password_confirm": "short"},
        headers={"x-csrftoken": csrf_token},
    )
    assert response.status_code == 200
    assert "almeno 8 caratteri" in response.text


async def test_post_registrati_with_mismatched_passwords_shows_error(client):
    """POST /registrati with mismatched passwords shows Italian error."""
    await client.get("/registrati")
    csrf_token = _get_csrf_token(client)

    response = await client.post(
        "/registrati",
        data={"email": "mismatch@example.com", "password": "validpass123", "password_confirm": "different123"},
        headers={"x-csrftoken": csrf_token},
    )
    assert response.status_code == 200
    assert "non corrispondono" in response.text


async def test_post_registrati_without_csrf_token_returns_403(client):
    """POST /registrati without CSRF token returns 403."""
    response = await client.post(
        "/registrati",
        data={"email": "nocsrf@example.com", "password": "validpass123", "password_confirm": "validpass123"},
    )
    assert response.status_code == 403


# --- Login tests ---


@pytest.fixture
async def registered_user(client):
    """Register a user via the API and return their credentials."""
    await client.get("/registrati")
    csrf = _get_csrf_token(client)
    await client.post(
        "/registrati",
        data={"email": "test@esempio.it", "password": "password123", "password_confirm": "password123"},
        headers={"x-csrftoken": csrf},
    )
    return {"email": "test@esempio.it", "password": "password123"}


async def test_get_accedi_returns_200_with_form(client):
    """GET /accedi returns 200 with the login form."""
    response = await client.get("/accedi")
    assert response.status_code == 200
    assert "Accedi" in response.text
    assert 'name="email"' in response.text
    assert 'name="password"' in response.text


async def test_post_accedi_with_valid_credentials_redirects_to_dashboard(client, registered_user):
    """POST /accedi with valid credentials redirects to /dashboard."""
    await client.get("/accedi")
    csrf = _get_csrf_token(client)
    response = await client.post(
        "/accedi",
        data={"email": registered_user["email"], "password": registered_user["password"]},
        headers={"x-csrftoken": csrf},
        follow_redirects=False,
    )
    assert response.status_code in (301, 302, 303)
    assert "/dashboard" in response.headers.get("location", "")


async def test_post_accedi_with_valid_credentials_sets_session(client, registered_user):
    """POST /accedi with valid credentials establishes a session (can access dashboard)."""
    await _login(client, registered_user["email"], registered_user["password"])
    assert "session" in client.cookies
    response = await client.get("/dashboard")
    assert response.status_code == 200
    assert registered_user["email"] in response.text


async def test_post_accedi_with_invalid_credentials_shows_italian_error(client):
    """POST /accedi with wrong credentials shows Italian error message."""
    await client.get("/accedi")
    csrf = _get_csrf_token(client)
    response = await client.post(
        "/accedi",
        data={"email": "nobody@example.com", "password": "wrongpassword"},
        headers={"x-csrftoken": csrf},
    )
    assert response.status_code == 200
    assert "Email o password non validi" in response.text


async def _login(client, email: str, password: str) -> str:
    """Login helper: sets session cookie, returns CSRF token."""
    await client.get("/accedi")
    csrf = _get_csrf_token(client)
    resp = await client.post(
        "/accedi",
        data={"email": email, "password": password},
        headers={"x-csrftoken": csrf},
        follow_redirects=False,
    )
    assert resp.status_code in (301, 302, 303)
    return csrf


async def test_post_esci_clears_session_and_redirects_to_accedi(client, registered_user):
    """POST /esci clears session and redirects to /accedi, session is destroyed."""
    csrf = await _login(client, registered_user["email"], registered_user["password"])
    # Verify session works before logout
    pre_logout = await client.get("/dashboard")
    assert pre_logout.status_code == 200
    # Logout
    response = await client.post(
        "/esci",
        headers={"x-csrftoken": csrf},
        follow_redirects=False,
    )
    assert response.status_code in (301, 302, 303)
    assert "/accedi" in response.headers.get("location", "")
    # Verify session is destroyed — dashboard should redirect to /accedi now
    post_logout = await client.get("/dashboard", follow_redirects=False)
    assert post_logout.status_code in (301, 302, 303)
    assert "/accedi" in post_logout.headers.get("location", "")


async def test_get_accedi_with_logout_success_msg_shows_italian_message(client, registered_user):
    """GET /accedi?msg=logout_success displays Italian logout confirmation."""
    response = await client.get("/accedi?msg=logout_success")
    assert response.status_code == 200
    assert "Disconnessione effettuata" in response.text


async def test_get_accedi_with_unknown_msg_shows_no_message(client):
    """GET /accedi?msg=unknown does not display any success message."""
    response = await client.get("/accedi?msg=unknown_key")
    assert response.status_code == 200
    assert "alert" not in response.text or 'data-variant="success"' not in response.text


async def test_post_esci_without_csrf_token_returns_403(client, registered_user):
    """POST /esci without CSRF token returns 403."""
    await _login(client, registered_user["email"], registered_user["password"])
    response = await client.post("/esci")
    assert response.status_code == 403


async def test_post_accedi_without_csrf_token_returns_403(client):
    """POST /accedi without CSRF token returns 403."""
    response = await client.post(
        "/accedi",
        data={"email": "test@example.com", "password": "password123"},
    )
    assert response.status_code == 403
