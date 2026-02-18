"""Constraint repository for data access."""

import uuid

from advanced_alchemy.repository import SQLAlchemyAsyncRepository
from sqlalchemy import select

from easyorario.models.constraint import Constraint


class ConstraintRepository(SQLAlchemyAsyncRepository[Constraint]):
    """Repository for Constraint persistence operations."""

    model_type = Constraint

    async def get_by_timetable(self, timetable_id: uuid.UUID) -> list[Constraint]:
        """Return all constraints for a timetable, ordered by created_at ascending."""
        stmt = select(Constraint).where(Constraint.timetable_id == timetable_id).order_by(Constraint.created_at)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
