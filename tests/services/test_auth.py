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


@pytest.fixture
async def auth_service(db_session):
    """AuthService backed by an in-memory database."""
    repo = UserRepository(session=db_session)
    return AuthService(user_repo=repo)


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


async def test_register_user_with_valid_input_creates_user(auth_service):
    """register_user creates a user with hashed password for valid input."""
    user = await auth_service.register_user("new@example.com", "validpass123")
    assert user.email == "new@example.com"
    assert user.hashed_password.startswith("$argon2")
    assert user.role == "responsible_professor"


async def test_register_user_with_duplicate_email_raises_error(db_session, auth_service):
    """register_user raises EmailAlreadyTakenError for existing email."""
    existing = User(email="taken@example.com", hashed_password="hashed")
    db_session.add(existing)
    await db_session.flush()

    with pytest.raises(EmailAlreadyTakenError):
        await auth_service.register_user("taken@example.com", "validpass123")


async def test_register_user_with_short_password_raises_error(auth_service):
    """register_user raises PasswordTooShortError for password < 8 chars."""
    with pytest.raises(PasswordTooShortError):
        await auth_service.register_user("short@example.com", "short")


async def test_register_user_with_invalid_email_raises_error(auth_service):
    """register_user raises InvalidEmailError for malformed email."""
    with pytest.raises(InvalidEmailError):
        await auth_service.register_user("notanemail", "validpass123")


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
async def test_register_user_rejects_degenerate_emails(auth_service, bad_email):
    """register_user raises InvalidEmailError for degenerate email formats."""
    with pytest.raises(InvalidEmailError):
        await auth_service.register_user(bad_email, "validpass123")
