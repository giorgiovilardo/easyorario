"""Home page controller."""

from litestar import Controller, Request, get
from litestar.response import Redirect, Template


class HomeController(Controller):
    """Home page controller serving the landing page."""

    path = "/"

    @get()
    async def index(self, request: Request) -> Template | Redirect:
        """Render the home page, or redirect authenticated users to dashboard."""
        user_id = request.session.get("user_id") if request.session else None
        if user_id:
            return Redirect(path="/dashboard")
        return Template(template_name="pages/index.html")
