"""Shared test fixtures."""

import pytest
from litestar.testing import AsyncTestClient

from easyorario.app import create_app

TEST_DB_URL = "sqlite+aiosqlite://"


@pytest.fixture
async def client():
    """Async test client with in-memory database."""
    app = create_app(database_url=TEST_DB_URL)
    async with AsyncTestClient(app=app) as client:
        yield client
