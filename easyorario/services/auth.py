"""Authentication service for registration and password management."""

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from easyorario.exceptions import (
    EmailAlreadyTakenError,
    InvalidEmailError,
    PasswordTooShortError,
)
from easyorario.models.user import User
from easyorario.repositories.user import UserRepository

_ph = PasswordHasher()

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


class AuthService:
    """Handles user registration and credential validation."""

    def __init__(self, user_repo: UserRepository) -> None:
        self.user_repo = user_repo

    async def register_user(self, email: str, password: str, role: str = "responsible_professor") -> User:
        """Register a new user after validating input."""
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
        return await self.user_repo.add(user)
