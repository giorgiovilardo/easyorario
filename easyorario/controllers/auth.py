"""Authentication controller for registration, login, and logout."""

from dataclasses import dataclass
from typing import Annotated

import structlog
from litestar import Controller, Request, get, post
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.response import Redirect, Template

from easyorario.exceptions import (
    EmailAlreadyTakenError,
    InvalidCredentialsError,
    InvalidEmailError,
    PasswordTooShortError,
)
from easyorario.i18n.errors import MESSAGES
from easyorario.services.auth import AuthService

_log = structlog.get_logger()

_LOGIN_PAGE_MESSAGES: set[str] = {"registration_success", "logout_success"}


@dataclass
class RegisterFormData:
    email: str
    password: str
    password_confirm: str


@dataclass
class LoginFormData:
    email: str
    password: str


class AuthController(Controller):
    """Handles user registration, login, and logout."""

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
        """Render the login form."""
        context: dict[str, str] = {}
        if msg and msg in _LOGIN_PAGE_MESSAGES:
            context["success"] = MESSAGES[msg]
        return Template(template_name="pages/login.html", context=context)

    @post("/accedi")
    async def login(
        self,
        request: Request,
        data: Annotated[LoginFormData, Body(media_type=RequestEncodingType.URL_ENCODED)],
        auth_service: AuthService,
    ) -> Template | Redirect:
        """Process login form submission."""
        try:
            user = await auth_service.authenticate_user(data.email, data.password)
            request.clear_session()
            request.set_session({"user_id": str(user.id)})
            return Redirect(path="/dashboard")
        except InvalidCredentialsError:
            return Template(
                "pages/login.html",
                context={"error": MESSAGES["invalid_credentials"], "email_value": data.email},
            )

    @post("/esci")
    async def logout(self, request: Request) -> Redirect:
        """Clear session and redirect to login."""
        request.clear_session()
        return Redirect(path="/accedi?msg=logout_success")
