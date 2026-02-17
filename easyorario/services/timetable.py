"""Timetable service for business logic."""

import uuid

import structlog

from easyorario.exceptions import InvalidTimetableDataError
from easyorario.models.timetable import Timetable
from easyorario.repositories.timetable import TimetableRepository

_log = structlog.get_logger()


class TimetableService:
    """Handles timetable creation and validation."""

    def __init__(self, timetable_repo: TimetableRepository) -> None:
        self.timetable_repo = timetable_repo

    async def create_timetable(
        self,
        *,
        owner_id: uuid.UUID,
        class_identifier: str,
        school_year: str,
        weekly_hours_raw: str,
        subjects_raw: str,
        teachers_raw: str,
    ) -> Timetable:
        """Validate inputs, parse subjects/teachers, and create a draft timetable."""
        class_identifier = class_identifier.strip()
        if not class_identifier:
            raise InvalidTimetableDataError("class_identifier_required")
        if len(class_identifier) > 255:
            raise InvalidTimetableDataError("class_identifier_too_long")

        school_year = school_year.strip()
        if not school_year:
            raise InvalidTimetableDataError("school_year_required")

        try:
            weekly_hours = int(weekly_hours_raw)
        except ValueError, TypeError:
            raise InvalidTimetableDataError("weekly_hours_invalid") from None
        if weekly_hours < 1 or weekly_hours > 60:
            raise InvalidTimetableDataError("weekly_hours_invalid")

        subjects = [line.strip() for line in subjects_raw.splitlines() if line.strip()]
        if not subjects:
            raise InvalidTimetableDataError("subjects_required")

        teachers = self._parse_teachers(teachers_raw)

        timetable = Timetable(
            class_identifier=class_identifier,
            school_year=school_year,
            weekly_hours=weekly_hours,
            subjects=subjects,
            teachers=teachers,
            owner_id=owner_id,
        )
        created = await self.timetable_repo.add(timetable)
        await _log.ainfo("timetable_created", timetable_id=str(created.id), owner=str(owner_id))
        return created

    @staticmethod
    def _parse_teachers(teachers_raw: str) -> dict[str, str]:
        """Parse 'Subject: Teacher' lines into a dict."""
        teachers: dict[str, str] = {}
        for line in teachers_raw.splitlines():
            line = line.strip()
            if not line:
                continue
            if ":" not in line:
                raise InvalidTimetableDataError("teachers_format_invalid")
            subject, _, teacher = line.partition(":")
            subject = subject.strip()
            teacher = teacher.strip()
            if not subject or not teacher:
                raise InvalidTimetableDataError("teachers_format_invalid")
            teachers[subject] = teacher
        return teachers
