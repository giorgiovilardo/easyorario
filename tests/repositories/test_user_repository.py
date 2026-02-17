"""Tests for UserRepository."""

from easyorario.models.user import User
from easyorario.repositories.user import UserRepository


async def test_get_by_email_returns_user_when_exists(db_session):
    """get_by_email returns the user when email matches."""
    user = User(email="found@example.com", hashed_password="hashed")
    db_session.add(user)
    await db_session.flush()

    repo = UserRepository(session=db_session)
    result = await repo.get_by_email("found@example.com")
    assert result is not None
    assert result.email == "found@example.com"


async def test_get_by_email_returns_none_when_not_found(db_session):
    """get_by_email returns None when no user has that email."""
    repo = UserRepository(session=db_session)
    result = await repo.get_by_email("nobody@example.com")
    assert result is None
