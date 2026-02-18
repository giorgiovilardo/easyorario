"""Tests for the ConstraintRepository."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from easyorario.models.constraint import Constraint
from easyorario.models.timetable import Timetable
from easyorario.models.user import User
from easyorario.repositories.constraint import ConstraintRepository


@pytest.fixture
async def user(db_session: AsyncSession) -> User:
    user = User(email="owner@example.com", hashed_password="x", role="responsible_professor")
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def timetable(db_session: AsyncSession, user: User) -> Timetable:
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


@pytest.fixture
async def constraint_repo(db_session: AsyncSession) -> ConstraintRepository:
    return ConstraintRepository(session=db_session)


async def test_add_constraint_persists(
    db_session: AsyncSession, timetable: Timetable, constraint_repo: ConstraintRepository
):
    """Adding a constraint should persist it in the database."""
    constraint = Constraint(
        timetable_id=timetable.id,
        natural_language_text="Prof. Rossi non puo insegnare il lunedi mattina",
    )
    created = await constraint_repo.add(constraint)
    await db_session.flush()

    assert created.id is not None
    assert created.natural_language_text == "Prof. Rossi non puo insegnare il lunedi mattina"
    assert created.status == "pending"


async def test_get_by_timetable_returns_ordered_list(
    db_session: AsyncSession, timetable: Timetable, constraint_repo: ConstraintRepository
):
    """Constraints should be returned ordered by created_at ascending."""
    c1 = Constraint(timetable_id=timetable.id, natural_language_text="Vincolo 1")
    c2 = Constraint(timetable_id=timetable.id, natural_language_text="Vincolo 2")
    db_session.add_all([c1, c2])
    await db_session.flush()

    results = await constraint_repo.get_by_timetable(timetable.id)

    assert len(results) == 2
    assert results[0].natural_language_text == "Vincolo 1"
    assert results[1].natural_language_text == "Vincolo 2"


async def test_get_by_timetable_returns_empty_for_other(
    db_session: AsyncSession, timetable: Timetable, constraint_repo: ConstraintRepository
):
    """Constraints from another timetable should not be returned."""
    c = Constraint(timetable_id=timetable.id, natural_language_text="Vincolo 1")
    db_session.add(c)
    await db_session.flush()

    other_id = uuid.uuid4()
    results = await constraint_repo.get_by_timetable(other_id)

    assert results == []
