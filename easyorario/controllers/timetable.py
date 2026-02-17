"""Timetable controller — stub routes for guard verification (Epic 2 will implement)."""

from litestar import Controller, Request, get
from litestar.response import Template

from easyorario.guards.auth import requires_responsible_professor


class TimetableController(Controller):
    """Placeholder timetable controller with role-guarded routes."""

    path = "/orario"

    @get("/nuovo", guards=[requires_responsible_professor])
    async def new_timetable(self, request: Request) -> Template:
        """Stub for new timetable creation — implemented in Epic 2."""
        return Template(
            template_name="pages/timetable_new.html",
            context={"user": request.user},
        )
