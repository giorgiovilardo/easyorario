"""Timetable repository for data access."""

import uuid

from advanced_alchemy.repository import SQLAlchemyAsyncRepository
from sqlalchemy import select

from easyorario.models.timetable import Timetable


class TimetableRepository(SQLAlchemyAsyncRepository[Timetable]):
    """Repository for Timetable persistence operations."""

    model_type = Timetable

    async def get_by_owner(self, owner_id: uuid.UUID) -> list[Timetable]:
        """Return all timetables owned by the given user."""
        stmt = select(Timetable).where(Timetable.owner_id == owner_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
