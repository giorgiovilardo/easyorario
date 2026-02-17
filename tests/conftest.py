"""Shared test fixtures."""

import pytest
from litestar.testing import AsyncTestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from easyorario.app import create_app
from easyorario.models.base import Base

TEST_DB_URL = "sqlite+aiosqlite://"


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
