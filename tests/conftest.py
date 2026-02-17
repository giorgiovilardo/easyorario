"""Shared test fixtures."""

import pytest
from litestar.testing import AsyncTestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from easyorario.app import create_app
from easyorario.models.base import Base

TEST_DB_URL = "sqlite+aiosqlite://"


def _get_csrf_token(client) -> str:
    """Get CSRF token from the client's cookie jar."""
    token = client.cookies.get("csrftoken")
    if not token:
        raise AssertionError("No CSRF cookie found in client cookie jar")
    return token


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


@pytest.fixture
async def client():
    """Async test client with in-memory database."""
    app = create_app(database_url=TEST_DB_URL, create_all=True, static_pool=True)
    async with AsyncTestClient(app=app) as client:
        yield client
    # Dispose the engine to prevent leaked connection warnings.
    # Advanced Alchemy stores engines under auto-incremented keys.
    for key in list(app.state._state):
        if key.startswith("db_engine"):
            await app.state._state[key].dispose()


@pytest.fixture
async def db_session():
    """Standalone async session with in-memory database for model/repo tests."""
    engine = create_async_engine(TEST_DB_URL, poolclass=StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSession(engine) as session:
        yield session
        await session.close()
    await engine.dispose()


@pytest.fixture
async def registered_user(client):
    """Register a user via the API, returning credentials dict."""
    await client.get("/registrati")
    csrf = client.cookies.get("csrftoken", "")
    await client.post(
        "/registrati",
        data={"email": "test@example.com", "password": "password123", "password_confirm": "password123"},
        headers={"x-csrftoken": csrf},
    )
    return {"email": "test@example.com", "password": "password123"}


@pytest.fixture
async def authenticated_client(client, registered_user):
    """Test client logged in as a Responsible Professor."""
    await _login(client, registered_user["email"], registered_user["password"])
    return client


@pytest.fixture
async def professor_user(client):
    """Register a Professor user (not Responsible Professor) via API + direct role update."""
    await client.get("/registrati")
    csrf = client.cookies.get("csrftoken", "")
    await client.post(
        "/registrati",
        data={"email": "prof@esempio.it", "password": "password123", "password_confirm": "password123"},
        headers={"x-csrftoken": csrf},
    )
    # Update role directly in DB — no UI for professor registration
    from sqlalchemy import text

    app = client.app
    for key in list(app.state._state):
        if key.startswith("db_engine"):
            engine = app.state._state[key]
            async with engine.begin() as conn:
                await conn.execute(text("UPDATE users SET role = 'professor' WHERE email = 'prof@esempio.it'"))
            break
    return {"email": "prof@esempio.it", "password": "password123"}


@pytest.fixture
async def authenticated_professor_client(client, professor_user):
    """Test client logged in as a Professor (not Responsible Professor)."""
    await _login(client, professor_user["email"], professor_user["password"])
    return client
