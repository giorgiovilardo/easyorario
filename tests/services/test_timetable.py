"""Tests for TimetableService."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from easyorario.exceptions import InvalidTimetableDataError
from easyorario.models.user import User
from easyorario.repositories.timetable import TimetableRepository
from easyorario.services.auth import hash_password
from easyorario.services.timetable import TimetableService


@pytest.fixture
async def owner(db_session: AsyncSession) -> User:
    """Create and persist a user to act as timetable owner."""
    user = User(email="owner@example.com", hashed_password=hash_password("password123"))
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
def timetable_service(db_session: AsyncSession) -> TimetableService:
    repo = TimetableRepository(session=db_session)
    return TimetableService(timetable_repo=repo)


async def test_create_timetable_with_valid_data_returns_draft(timetable_service: TimetableService, owner: User) -> None:
    """Creating a timetable with valid data returns a draft timetable."""
    timetable = await timetable_service.create_timetable(
        owner_id=owner.id,
        class_identifier="3A Liceo Scientifico",
        school_year="2026/2027",
        weekly_hours_raw="30",
        subjects_raw="Matematica\nItaliano\nFisica",
        teachers_raw="Matematica: Prof. Rossi\nItaliano: Prof. Bianchi",
    )
    assert timetable.status == "draft"
    assert timetable.class_identifier == "3A Liceo Scientifico"
    assert timetable.school_year == "2026/2027"
    assert timetable.weekly_hours == 30
    assert timetable.subjects == ["Matematica", "Italiano", "Fisica"]
    assert timetable.teachers == {"Matematica": "Prof. Rossi", "Italiano": "Prof. Bianchi"}
    assert timetable.owner_id == owner.id
    assert isinstance(timetable.id, uuid.UUID)


async def test_create_timetable_with_empty_teachers_succeeds(timetable_service: TimetableService, owner: User) -> None:
    """Teachers are optional — empty string should produce empty dict."""
    timetable = await timetable_service.create_timetable(
        owner_id=owner.id,
        class_identifier="2B",
        school_year="2026/2027",
        weekly_hours_raw="27",
        subjects_raw="Storia",
        teachers_raw="",
    )
    assert timetable.teachers == {}


async def test_create_timetable_with_empty_class_identifier_raises(
    timetable_service: TimetableService, owner: User
) -> None:
    """Empty class_identifier raises InvalidTimetableDataError."""
    with pytest.raises(InvalidTimetableDataError) as exc_info:
        await timetable_service.create_timetable(
            owner_id=owner.id,
            class_identifier="",
            school_year="2026/2027",
            weekly_hours_raw="30",
            subjects_raw="Matematica",
            teachers_raw="",
        )
    assert exc_info.value.error_key == "class_identifier_required"


async def test_create_timetable_with_zero_weekly_hours_raises(timetable_service: TimetableService, owner: User) -> None:
    """weekly_hours < 1 raises InvalidTimetableDataError."""
    with pytest.raises(InvalidTimetableDataError) as exc_info:
        await timetable_service.create_timetable(
            owner_id=owner.id,
            class_identifier="3A",
            school_year="2026/2027",
            weekly_hours_raw="0",
            subjects_raw="Matematica",
            teachers_raw="",
        )
    assert exc_info.value.error_key == "weekly_hours_invalid"


async def test_create_timetable_with_non_numeric_weekly_hours_raises(
    timetable_service: TimetableService, owner: User
) -> None:
    """Non-numeric weekly_hours raises InvalidTimetableDataError."""
    with pytest.raises(InvalidTimetableDataError) as exc_info:
        await timetable_service.create_timetable(
            owner_id=owner.id,
            class_identifier="3A",
            school_year="2026/2027",
            weekly_hours_raw="abc",
            subjects_raw="Matematica",
            teachers_raw="",
        )
    assert exc_info.value.error_key == "weekly_hours_invalid"


async def test_create_timetable_with_empty_school_year_raises(timetable_service: TimetableService, owner: User) -> None:
    """Empty school_year raises InvalidTimetableDataError."""
    with pytest.raises(InvalidTimetableDataError) as exc_info:
        await timetable_service.create_timetable(
            owner_id=owner.id,
            class_identifier="3A",
            school_year="",
            weekly_hours_raw="30",
            subjects_raw="Matematica",
            teachers_raw="",
        )
    assert exc_info.value.error_key == "school_year_required"


async def test_create_timetable_with_no_subjects_raises(timetable_service: TimetableService, owner: User) -> None:
    """Empty subjects list raises InvalidTimetableDataError."""
    with pytest.raises(InvalidTimetableDataError) as exc_info:
        await timetable_service.create_timetable(
            owner_id=owner.id,
            class_identifier="3A",
            school_year="2026/2027",
            weekly_hours_raw="30",
            subjects_raw="",
            teachers_raw="",
        )
    assert exc_info.value.error_key == "subjects_required"


async def test_create_timetable_with_class_identifier_over_255_chars_raises(
    timetable_service: TimetableService, owner: User
) -> None:
    """class_identifier exceeding 255 characters raises InvalidTimetableDataError."""
    with pytest.raises(InvalidTimetableDataError) as exc_info:
        await timetable_service.create_timetable(
            owner_id=owner.id,
            class_identifier="A" * 256,
            school_year="2026/2027",
            weekly_hours_raw="30",
            subjects_raw="Matematica",
            teachers_raw="",
        )
    assert exc_info.value.error_key == "class_identifier_too_long"


async def test_create_timetable_with_invalid_teacher_format_raises(
    timetable_service: TimetableService, owner: User
) -> None:
    """Teacher line without colon raises InvalidTimetableDataError."""
    with pytest.raises(InvalidTimetableDataError) as exc_info:
        await timetable_service.create_timetable(
            owner_id=owner.id,
            class_identifier="3A",
            school_year="2026/2027",
            weekly_hours_raw="30",
            subjects_raw="Matematica",
            teachers_raw="Matematica Prof. Rossi",
        )
    assert exc_info.value.error_key == "teachers_format_invalid"


async def test_create_timetable_with_empty_teacher_name_raises(
    timetable_service: TimetableService, owner: User
) -> None:
    """Teacher line with empty name after colon raises InvalidTimetableDataError."""
    with pytest.raises(InvalidTimetableDataError) as exc_info:
        await timetable_service.create_timetable(
            owner_id=owner.id,
            class_identifier="3A",
            school_year="2026/2027",
            weekly_hours_raw="30",
            subjects_raw="Matematica",
            teachers_raw="Matematica:",
        )
    assert exc_info.value.error_key == "teachers_format_invalid"


async def test_create_timetable_with_weekly_hours_over_60_raises(
    timetable_service: TimetableService, owner: User
) -> None:
    """weekly_hours > 60 raises InvalidTimetableDataError."""
    with pytest.raises(InvalidTimetableDataError) as exc_info:
        await timetable_service.create_timetable(
            owner_id=owner.id,
            class_identifier="3A",
            school_year="2026/2027",
            weekly_hours_raw="61",
            subjects_raw="Matematica",
            teachers_raw="",
        )
    assert exc_info.value.error_key == "weekly_hours_invalid"
