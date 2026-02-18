"""Constraint service for business logic."""

import uuid

import structlog

from easyorario.exceptions import InvalidConstraintDataError
from easyorario.models.constraint import Constraint
from easyorario.repositories.constraint import ConstraintRepository

_log = structlog.get_logger()


class ConstraintService:
    """Handles constraint creation and validation."""

    def __init__(self, constraint_repo: ConstraintRepository) -> None:
        self.constraint_repo = constraint_repo

    async def add_constraint(
        self,
        *,
        timetable_id: uuid.UUID,
        natural_language_text: str,
    ) -> Constraint:
        """Validate and create a new pending constraint."""
        text = natural_language_text.strip()
        if not text:
            raise InvalidConstraintDataError("constraint_text_required")
        if len(text) > 1000:
            raise InvalidConstraintDataError("constraint_text_too_long")

        constraint = Constraint(
            timetable_id=timetable_id,
            natural_language_text=text,
        )
        created = await self.constraint_repo.add(constraint)
        await _log.ainfo("constraint_added", constraint_id=str(created.id), timetable_id=str(timetable_id))
        return created

    async def list_constraints(self, *, timetable_id: uuid.UUID) -> list[Constraint]:
        """Return all constraints for a timetable, ordered by created_at."""
        return await self.constraint_repo.get_by_timetable(timetable_id)
