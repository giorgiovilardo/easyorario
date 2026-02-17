"""Authentication and authorization guards."""

from litestar.connection import ASGIConnection
from litestar.exceptions import ImproperlyConfiguredException, NotAuthorizedException
from litestar.handlers import BaseRouteHandler


def requires_login(connection: ASGIConnection, _: BaseRouteHandler) -> None:
    """Ensure user is authenticated."""
    if not connection.user:
        raise NotAuthorizedException(detail="Login required")


def requires_role(connection: ASGIConnection, handler: BaseRouteHandler) -> None:
    """Ensure user has the required role (set via handler opt).

    Raises ImproperlyConfiguredException if applied without ``required_role`` in opt.
    """
    required_role = handler.opt.get("required_role")
    if not required_role:
        raise ImproperlyConfiguredException("requires_role guard requires 'required_role' in handler opt")
    if not connection.user or connection.user.role != required_role:
        raise NotAuthorizedException(detail="Insufficient permissions")


def requires_responsible_professor(connection: ASGIConnection, _: BaseRouteHandler) -> None:
    """Ensure user is a Responsible Professor."""
    if not connection.user or connection.user.role != "responsible_professor":
        raise NotAuthorizedException(detail="Insufficient permissions")
