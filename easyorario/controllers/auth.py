"""Authentication controller for registration endpoints."""

from dataclasses import dataclass
from typing import Annotated

from litestar import Controller, get, post
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.response import Redirect, Template

from easyorario.exceptions import (
    EmailAlreadyTakenError,
    InvalidEmailError,
    PasswordTooShortError,
)
from easyorario.i18n.errors import MESSAGES
from easyorario.services.auth import AuthService


@dataclass
class RegisterFormData:
    email: str
    password: str
    password_confirm: str


class AuthController(Controller):
    """Handles user registration and login placeholder."""

    path = ""

    @get("/registrati")
    async def show_register(self) -> Template:
        """Render the registration form."""
        return Template(template_name="pages/register.html")

    @post("/registrati")
    async def register(
        self,
        data: Annotated[RegisterFormData, Body(media_type=RequestEncodingType.URL_ENCODED)],
        auth_service: AuthService,
    ) -> Template | Redirect:
        """Process registration form submission."""
        if data.password != data.password_confirm:
            return Template(
                "pages/register.html",
                context={"error": MESSAGES["password_mismatch"], "email_value": data.email},
            )

        try:
            await auth_service.register_user(data.email, data.password)
            return Redirect(path="/accedi?msg=registration_success")
        except (EmailAlreadyTakenError, PasswordTooShortError, InvalidEmailError) as exc:
            return Template(
                "pages/register.html",
                context={"error": MESSAGES[exc.error_key], "email_value": data.email},
            )

    @get("/accedi")
    async def show_login(self, msg: str | None = None) -> Template:
        """Render the login placeholder page."""
        context: dict[str, str] = {}
        if msg and msg in MESSAGES:
            context["success"] = MESSAGES[msg]
        return Template(template_name="pages/login.html", context=context)
