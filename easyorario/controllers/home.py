"""Home page controller."""

from litestar import Controller, get
from litestar.response import Template


class HomeController(Controller):
    """Home page controller serving the landing page."""

    path = "/"

    @get()
    async def index(self) -> Template:
        """Render the home page."""
        return Template(template_name="pages/index.html")
