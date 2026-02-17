"""Tests for User model."""

import uuid

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from easyorario.models.user import User


async def test_user_model_has_correct_tablename():
    """User model uses 'users' as table name."""
    assert User.__tablename__ == "users"


async def test_user_model_has_required_columns():
    """User model defines all required columns: id, email, hashed_password, role, created_at."""
    mapper = inspect(User)
    column_names = {col.key for col in mapper.column_attrs}
    assert column_names == {"id", "email", "hashed_password", "role", "created_at"}


async def test_user_model_id_defaults_to_uuid(db_session):
    """User id defaults to a UUID value after persistence."""
    user = User(email="test@example.com", hashed_password="hashed")
    db_session.add(user)
    await db_session.flush()
    assert isinstance(user.id, uuid.UUID)


async def test_user_model_role_defaults_to_responsible_professor(db_session):
    """User role defaults to 'responsible_professor'."""
    user = User(email="role@example.com", hashed_password="hashed")
    db_session.add(user)
    await db_session.flush()
    assert user.role == "responsible_professor"


async def test_user_model_email_unique_constraint(db_session):
    """Users table has a unique constraint on email column."""
    user1 = User(email="dup@example.com", hashed_password="hashed1")
    db_session.add(user1)
    await db_session.flush()

    user2 = User(email="dup@example.com", hashed_password="hashed2")
    db_session.add(user2)
    with pytest.raises(IntegrityError, match="(?i)unique"):
        await db_session.flush()
