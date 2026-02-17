"""Tests for AuthService."""

import pytest

from easyorario.exceptions import (
    EmailAlreadyTakenError,
    InvalidEmailError,
    PasswordTooShortError,
)
from easyorario.models.user import User
from easyorario.repositories.user import UserRepository
from easyorario.services.auth import AuthService, hash_password, verify_password


async def test_hash_password_returns_argon2_hash():
    """hash_password returns a string starting with the Argon2 prefix."""
    hashed = hash_password("securepass")
    assert hashed.startswith("$argon2")


async def test_verify_password_matches_correct_password():
    """verify_password returns True for correct password."""
    hashed = hash_password("securepass")
    assert verify_password(hashed, "securepass") is True


async def test_verify_password_rejects_wrong_password():
    """verify_password returns False for wrong password."""
    hashed = hash_password("securepass")
    assert verify_password(hashed, "wrongpass") is False


async def test_register_user_with_valid_input_creates_user(db_session):
    """register_user creates a user with hashed password for valid input."""
    repo = UserRepository(session=db_session)
    service = AuthService(user_repo=repo)
    user = await service.register_user("new@example.com", "validpass123")
    assert user.email == "new@example.com"
    assert user.hashed_password.startswith("$argon2")
    assert user.role == "responsible_professor"


async def test_register_user_with_duplicate_email_raises_error(db_session):
    """register_user raises EmailAlreadyTakenError for existing email."""
    existing = User(email="taken@example.com", hashed_password="hashed")
    db_session.add(existing)
    await db_session.flush()

    repo = UserRepository(session=db_session)
    service = AuthService(user_repo=repo)
    with pytest.raises(EmailAlreadyTakenError):
        await service.register_user("taken@example.com", "validpass123")


async def test_register_user_with_short_password_raises_error(db_session):
    """register_user raises PasswordTooShortError for password < 8 chars."""
    repo = UserRepository(session=db_session)
    service = AuthService(user_repo=repo)
    with pytest.raises(PasswordTooShortError):
        await service.register_user("short@example.com", "short")


async def test_register_user_with_invalid_email_raises_error(db_session):
    """register_user raises InvalidEmailError for malformed email."""
    repo = UserRepository(session=db_session)
    service = AuthService(user_repo=repo)
    with pytest.raises(InvalidEmailError):
        await service.register_user("notanemail", "validpass123")


@pytest.mark.parametrize(
    "bad_email",
    [
        "@foo.com",  # no local part
        "user@",  # no domain
        "user@.com",  # domain starts with dot
        "user@foo.",  # domain ends with dot
        "",  # empty string
    ],
)
async def test_register_user_rejects_degenerate_emails(db_session, bad_email):
    """register_user raises InvalidEmailError for degenerate email formats."""
    repo = UserRepository(session=db_session)
    service = AuthService(user_repo=repo)
    with pytest.raises(InvalidEmailError):
        await service.register_user(bad_email, "validpass123")
