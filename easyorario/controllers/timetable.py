"""Timetable controller — create timetable form."""

from dataclasses import dataclass
from typing import Annotated

import structlog
from litestar import Controller, Request, get, post
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.response import Redirect, Template

from easyorario.exceptions import InvalidTimetableDataError
from easyorario.guards.auth import requires_responsible_professor
from easyorario.i18n.errors import MESSAGES
from easyorario.services.timetable import TimetableService

_log = structlog.get_logger()


@dataclass
class TimetableFormData:
    class_identifier: str = ""
    school_year: str = ""
    weekly_hours: str = ""
    subjects: str = ""
    teachers: str = ""


class TimetableController(Controller):
    """Timetable creation and constraints management."""

    path = "/orario"

    @get("/nuovo", guards=[requires_responsible_professor])
    async def new_timetable(self, request: Request) -> Template:
        """Render the create timetable form."""
        return Template(
            template_name="pages/timetable_new.html",
            context={"user": request.user},
        )

    @post("/nuovo", guards=[requires_responsible_professor])
    async def create_timetable(
        self,
        request: Request,
        data: Annotated[TimetableFormData, Body(media_type=RequestEncodingType.URL_ENCODED)],
        timetable_service: TimetableService,
    ) -> Template | Redirect:
        """Process create timetable form submission."""
        try:
            timetable = await timetable_service.create_timetable(
                owner_id=request.user.id,
                class_identifier=data.class_identifier,
                school_year=data.school_year,
                weekly_hours_raw=data.weekly_hours,
                subjects_raw=data.subjects,
                teachers_raw=data.teachers,
            )
            return Redirect(path=f"/orario/{timetable.id}/vincoli")
        except InvalidTimetableDataError as exc:
            return Template(
                "pages/timetable_new.html",
                context={
                    "error": MESSAGES[exc.error_key],
                    "user": request.user,
                    "form": data,
                },
            )
