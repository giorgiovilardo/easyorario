"""Tests for the Timetable ORM model."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from easyorario.models.timetable import Timetable
from easyorario.models.user import User
from easyorario.services.auth import hash_password


@pytest.fixture
async def owner(db_session: AsyncSession) -> User:
    """Create and persist a user to act as timetable owner."""
    user = User(email="owner@example.com", hashed_password=hash_password("password123"))
    db_session.add(user)
    await db_session.flush()
    return user


async def test_create_timetable_model_has_correct_defaults(db_session: AsyncSession, owner: User) -> None:
    """New timetable defaults to status='draft' and has created_at set."""
    timetable = Timetable(
        class_identifier="3A Liceo Scientifico",
        school_year="2026/2027",
        weekly_hours=30,
        subjects=["Matematica", "Italiano"],
        teachers={"Matematica": "Prof. Rossi"},
        owner_id=owner.id,
    )
    db_session.add(timetable)
    await db_session.flush()
    await db_session.refresh(timetable)

    assert timetable.status == "draft"
    assert timetable.created_at is not None
    assert isinstance(timetable.id, uuid.UUID)


async def test_timetable_owner_relationship_links_to_user(db_session: AsyncSession, owner: User) -> None:
    """Timetable.owner resolves to the related User."""
    timetable = Timetable(
        class_identifier="1B",
        school_year="2026/2027",
        weekly_hours=27,
        subjects=["Storia"],
        teachers={},
        owner_id=owner.id,
    )
    db_session.add(timetable)
    await db_session.flush()
    await db_session.refresh(timetable)

    assert timetable.owner.id == owner.id
    assert timetable.owner.email == "owner@example.com"
