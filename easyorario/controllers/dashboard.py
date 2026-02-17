"""Dashboard controller — minimal placeholder for login redirect target."""

from litestar import Controller, get
from litestar.response import Template

from easyorario.guards.auth import requires_login


class DashboardController(Controller):
    """Placeholder dashboard (full implementation in story 1.4)."""

    path = "/dashboard"
    guards = [requires_login]

    @get("/")
    async def show_dashboard(self) -> Template:
        """Render the dashboard page."""
        return Template(template_name="pages/dashboard.html")
