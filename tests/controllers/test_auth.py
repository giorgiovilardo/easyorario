"""Tests for AuthController registration endpoints."""


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
