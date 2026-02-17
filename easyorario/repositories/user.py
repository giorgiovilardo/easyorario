"""User repository for data access."""

from advanced_alchemy.repository import SQLAlchemyAsyncRepository
from sqlalchemy import select

from easyorario.models.user import User


class UserRepository(SQLAlchemyAsyncRepository[User]):
    """Repository for User persistence operations."""

    model_type = User

    async def get_by_email(self, email: str) -> User | None:
        """Return user with given email, or None if not found."""
        stmt = select(User).where(User.email == email)
        return (await self.session.execute(stmt)).scalar_one_or_none()
