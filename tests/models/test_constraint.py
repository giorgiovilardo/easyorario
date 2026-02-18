"""Tests for the Constraint ORM model."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from easyorario.models.constraint import Constraint
from easyorario.models.timetable import Timetable
from easyorario.models.user import User


@pytest.fixture
async def user(db_session: AsyncSession) -> User:
    """Create a user for ownership."""
    user = User(email="owner@example.com", hashed_password="x", role="responsible_professor")
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def timetable(db_session: AsyncSession, user: User) -> Timetable:
    """Create a timetable for FK references."""
    tt = Timetable(
        class_identifier="3A",
        school_year="2025-2026",
        weekly_hours=30,
        subjects=["Matematica"],
        teachers={"Matematica": "Prof. Rossi"},
        owner_id=user.id,
    )
    db_session.add(tt)
    await db_session.flush()
    return tt


async def test_create_constraint_has_correct_defaults(db_session: AsyncSession, timetable: Timetable):
    """New constraint should have status='pending', formal_representation=None, and created_at set."""
    constraint = Constraint(
        timetable_id=timetable.id,
        natural_language_text="Prof. Rossi non puo insegnare il lunedi mattina",
    )
    db_session.add(constraint)
    await db_session.flush()

    assert constraint.id is not None
    assert isinstance(constraint.id, uuid.UUID)
    assert constraint.status == "pending"
    assert constraint.formal_representation is None
    assert constraint.created_at is not None


async def test_constraint_timetable_relationship(db_session: AsyncSession, timetable: Timetable):
    """Constraint should link to its timetable via the relationship."""
    constraint = Constraint(
        timetable_id=timetable.id,
        natural_language_text="Nessuna lezione dopo le 14",
    )
    db_session.add(constraint)
    await db_session.flush()
    await db_session.refresh(constraint)

    assert constraint.timetable.id == timetable.id
    assert constraint.timetable.class_identifier == "3A"
