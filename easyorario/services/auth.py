"""Authentication service for registration and password management."""

import structlog
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from easyorario.exceptions import (
    EmailAlreadyTakenError,
    InvalidCredentialsError,
    InvalidEmailError,
    PasswordTooShortError,
)
from easyorario.models.user import User
from easyorario.repositories.user import UserRepository

_ph = PasswordHasher()
_log = structlog.get_logger()

MIN_PASSWORD_LENGTH = 8


def hash_password(password: str) -> str:
    """Hash a password using Argon2."""
    return _ph.hash(password)


def verify_password(hashed_password: str, password: str) -> bool:
    """Verify a password against its Argon2 hash."""
    try:
        return _ph.verify(hashed_password, password)
    except VerifyMismatchError:
        return False


def _normalize_email(email: str) -> str:
    """Lowercase and strip whitespace from email."""
    return email.lower().strip()


class AuthService:
    """Handles user registration and credential validation."""

    def __init__(self, user_repo: UserRepository) -> None:
        self.user_repo = user_repo

    async def register_user(self, email: str, password: str, role: str = "responsible_professor") -> User:
        """Register a new user after validating input."""
        email = _normalize_email(email)

        if "@" not in email:
            raise InvalidEmailError
        local, domain = email.rsplit("@", 1)
        if not local or not domain or "." not in domain or domain.startswith(".") or domain.endswith("."):
            raise InvalidEmailError

        if len(password) < MIN_PASSWORD_LENGTH:
            raise PasswordTooShortError

        if await self.user_repo.get_by_email(email):
            raise EmailAlreadyTakenError

        user = User(
            email=email,
            hashed_password=hash_password(password),
            role=role,
        )
        created = await self.user_repo.add(user)
        await _log.ainfo("user_registered", email=email)
        return created

    async def authenticate_user(self, email: str, password: str) -> User:
        """Verify credentials and return user, or raise InvalidCredentialsError."""
        email = _normalize_email(email)
        user = await self.user_repo.get_by_email(email)
        if not user or not verify_password(user.hashed_password, password):
            await _log.awarning("login_failed", email=email)
            raise InvalidCredentialsError
        if _ph.check_needs_rehash(user.hashed_password):
            user.hashed_password = hash_password(password)
            await _log.ainfo("password_rehashed", email=email)
        await _log.ainfo("login_succeeded", email=email)
        return user
