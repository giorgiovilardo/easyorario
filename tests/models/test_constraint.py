"""Tests for the Constraint ORM model."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from easyorario.models.constraint import Constraint
from easyorario.models.timetable import Timetable


async def test_create_constraint_has_correct_defaults(db_session: AsyncSession, db_timetable: Timetable):
    """New constraint should have status='pending', formal_representation=None, and created_at set."""
    constraint = Constraint(
        timetable_id=db_timetable.id,
        natural_language_text="Prof. Rossi non puo insegnare il lunedi mattina",
    )
    db_session.add(constraint)
    await db_session.flush()

    assert constraint.id is not None
    assert isinstance(constraint.id, uuid.UUID)
    assert constraint.status == "pending"
    assert constraint.formal_representation is None
    assert constraint.created_at is not None


async def test_constraint_timetable_relationship(db_session: AsyncSession, db_timetable: Timetable):
    """Constraint should link to its timetable via the relationship."""
    constraint = Constraint(
        timetable_id=db_timetable.id,
        natural_language_text="Nessuna lezione dopo le 14",
    )
    db_session.add(constraint)
    await db_session.flush()
    await db_session.refresh(constraint)

    assert constraint.timetable.id == db_timetable.id
    assert constraint.timetable.class_identifier == "3A"
