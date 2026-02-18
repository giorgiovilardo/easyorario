"""Tests for the ConstraintService."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from easyorario.exceptions import InvalidConstraintDataError
from easyorario.models.timetable import Timetable
from easyorario.models.user import User
from easyorario.repositories.constraint import ConstraintRepository
from easyorario.services.constraint import ConstraintService


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
async def constraint_service(db_session: AsyncSession) -> ConstraintService:
    repo = ConstraintRepository(session=db_session)
    return ConstraintService(constraint_repo=repo)


async def test_add_constraint_with_valid_text_creates_pending(
    db_session: AsyncSession, timetable: Timetable, constraint_service: ConstraintService
):
    """Adding a constraint with valid text should create it with status='pending'."""
    constraint = await constraint_service.add_constraint(
        timetable_id=timetable.id,
        natural_language_text="Prof. Rossi non puo insegnare il lunedi mattina",
    )

    assert constraint.id is not None
    assert constraint.natural_language_text == "Prof. Rossi non puo insegnare il lunedi mattina"
    assert constraint.status == "pending"
    assert constraint.timetable_id == timetable.id


async def test_add_constraint_with_empty_text_raises(timetable: Timetable, constraint_service: ConstraintService):
    """Empty or whitespace-only text should raise InvalidConstraintDataError."""
    with pytest.raises(InvalidConstraintDataError) as exc_info:
        await constraint_service.add_constraint(
            timetable_id=timetable.id,
            natural_language_text="   ",
        )
    assert exc_info.value.error_key == "constraint_text_required"


async def test_add_constraint_with_text_over_1000_chars_raises(
    timetable: Timetable, constraint_service: ConstraintService
):
    """Text exceeding 1000 characters should raise InvalidConstraintDataError."""
    long_text = "a" * 1001
    with pytest.raises(InvalidConstraintDataError) as exc_info:
        await constraint_service.add_constraint(
            timetable_id=timetable.id,
            natural_language_text=long_text,
        )
    assert exc_info.value.error_key == "constraint_text_too_long"


async def test_list_constraints_returns_ordered(
    db_session: AsyncSession, timetable: Timetable, constraint_service: ConstraintService
):
    """list_constraints should return constraints ordered by created_at ascending."""
    await constraint_service.add_constraint(
        timetable_id=timetable.id,
        natural_language_text="Vincolo 1",
    )
    await constraint_service.add_constraint(
        timetable_id=timetable.id,
        natural_language_text="Vincolo 2",
    )
    await db_session.flush()

    results = await constraint_service.list_constraints(timetable_id=timetable.id)

    assert len(results) == 2
    assert results[0].natural_language_text == "Vincolo 1"
    assert results[1].natural_language_text == "Vincolo 2"
