"""Tests for database configuration."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from easyorario.app import _set_sqlite_pragmas


async def test_sqlite_wal_mode_is_active(tmp_path):
    """SQLite WAL mode is enabled on file-based database connections."""
    db_path = tmp_path / "test_wal.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

    # Register the same pragma listener used in production
    from sqlalchemy import event

    event.listen(engine.sync_engine, "connect", _set_sqlite_pragmas)

    async with engine.connect() as conn:
        result = await conn.execute(text("PRAGMA journal_mode"))
        mode = result.scalar()
        assert mode == "wal"

    await engine.dispose()
