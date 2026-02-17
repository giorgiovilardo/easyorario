"""Tests for TimetableRepository."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from easyorario.models.timetable import Timetable
from easyorario.models.user import User
from easyorario.repositories.timetable import TimetableRepository
from easyorario.services.auth import hash_password


@pytest.fixture
async def owner(db_session: AsyncSession) -> User:
    """Create and persist a user to act as timetable owner."""
    user = User(email="owner@example.com", hashed_password=hash_password("password123"))
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def other_owner(db_session: AsyncSession) -> User:
    """Create a second user to test ownership filtering."""
    user = User(email="other@example.com", hashed_password=hash_password("password123"))
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
def timetable_repo(db_session: AsyncSession) -> TimetableRepository:
    return TimetableRepository(session=db_session)


async def test_add_timetable_persists_to_database(timetable_repo: TimetableRepository, owner: User) -> None:
    """Adding a timetable persists it and returns with an ID."""
    timetable = Timetable(
        class_identifier="3A Liceo Scientifico",
        school_year="2026/2027",
        weekly_hours=30,
        subjects=["Matematica", "Italiano"],
        teachers={"Matematica": "Prof. Rossi"},
        owner_id=owner.id,
    )
    created = await timetable_repo.add(timetable)
    assert isinstance(created.id, uuid.UUID)
    assert created.class_identifier == "3A Liceo Scientifico"
    assert created.status == "draft"


async def test_get_by_owner_returns_only_owned_timetables(
    timetable_repo: TimetableRepository, owner: User, other_owner: User
) -> None:
    """get_by_owner returns only timetables belonging to the specified user."""
    t1 = Timetable(
        class_identifier="3A",
        school_year="2026/2027",
        weekly_hours=30,
        subjects=["Matematica"],
        teachers={},
        owner_id=owner.id,
    )
    t2 = Timetable(
        class_identifier="2B",
        school_year="2026/2027",
        weekly_hours=27,
        subjects=["Italiano"],
        teachers={},
        owner_id=other_owner.id,
    )
    await timetable_repo.add(t1)
    await timetable_repo.add(t2)

    owned = await timetable_repo.get_by_owner(owner.id)
    assert len(owned) == 1
    assert owned[0].class_identifier == "3A"
