"""Health check endpoint."""

from dataclasses import dataclass

from litestar import Controller, get
from litestar.exceptions import ServiceUnavailableException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class HealthStatus:
    status: str


class HealthController(Controller):
    """Health check controller with DB connectivity verification."""

    path = "/health"

    @get()
    async def health_check(self, db_session: AsyncSession) -> HealthStatus:
        """Return health status with DB connectivity check."""
        try:
            await db_session.execute(text("SELECT 1"))
        except Exception as exc:
            raise ServiceUnavailableException(detail=str(exc)) from exc
        return HealthStatus(status="ok")
