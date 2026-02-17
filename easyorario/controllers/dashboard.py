"""Dashboard controller with role-aware rendering."""

from litestar import Controller, Request, get
from litestar.response import Template


class DashboardController(Controller):
    """Dashboard showing role-appropriate content."""

    path = "/dashboard"

    @get("/")
    async def show_dashboard(self, request: Request) -> Template:
        """Render the dashboard page with role-aware context."""
        user = request.user
        return Template(
            template_name="pages/dashboard.html",
            context={
                "user": user,
                "is_responsible": user.role == "responsible_professor",
            },
        )
