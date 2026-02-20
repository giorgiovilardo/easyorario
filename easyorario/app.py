"""Litestar application factory."""

import uuid
from pathlib import Path
from typing import Any

import structlog
from advanced_alchemy.extensions.litestar import (
    AlembicAsyncConfig,
    AsyncSessionConfig,
    EngineConfig,
    SQLAlchemyAsyncConfig,
    SQLAlchemyPlugin,
)
from advanced_alchemy.extensions.litestar.plugins.init.config.asyncio import autocommit_handler_maker
from litestar import Litestar, Request, Response
from litestar.config.csrf import CSRFConfig
from litestar.connection import ASGIConnection
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.di import Provide
from litestar.exceptions import NotAuthorizedException
from litestar.logging import StructLoggingConfig
from litestar.middleware.session.server_side import ServerSideSessionBackend, ServerSideSessionConfig
from litestar.plugins.structlog import StructlogConfig, StructlogPlugin
from litestar.response import Redirect, Template
from litestar.security.session_auth import SessionAuth
from litestar.static_files import create_static_files_router
from litestar.stores.memory import MemoryStore
from litestar.template.config import TemplateConfig
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.pool import StaticPool

from easyorario.config import settings
from easyorario.controllers.auth import AuthController
from easyorario.controllers.constraint import ConstraintController
from easyorario.controllers.dashboard import DashboardController
from easyorario.controllers.health import HealthController
from easyorario.controllers.home import HomeController
from easyorario.controllers.settings import SettingsController
from easyorario.controllers.timetable import TimetableController
from easyorario.i18n.errors import MESSAGES
from easyorario.models.base import Base
from easyorario.models.user import User
from easyorario.repositories.constraint import ConstraintRepository
from easyorario.repositories.timetable import TimetableRepository
from easyorario.repositories.user import UserRepository
from easyorario.services.auth import AuthService
from easyorario.services.constraint import ConstraintService
from easyorario.services.llm import LLMService
from easyorario.services.timetable import TimetableService

_BASE_DIR = Path(__file__).resolve().parent.parent
_log = structlog.get_logger()


def _set_sqlite_pragmas(dbapi_connection, connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def _auth_exception_handler(request: Request, _: NotAuthorizedException) -> Response:
    """Handle auth exceptions: redirect unauthenticated users, show 403 for wrong role."""
    user = request.scope.get("user")
    if not user:
        return Redirect(path="/accedi")
    _log.warning("forbidden_access", user_email=user.email, path=request.url.path)
    return Template(
        template_name="pages/errors/403.html",
        context={"error": MESSAGES["forbidden"], "user": user},
        status_code=403,
    )


async def provide_user_repository(db_session: AsyncSession) -> UserRepository:
    """Provide UserRepository via DI."""
    return UserRepository(session=db_session)


async def provide_auth_service(user_repo: UserRepository) -> AuthService:
    """Provide AuthService via DI."""
    return AuthService(user_repo=user_repo)


async def provide_timetable_repository(db_session: AsyncSession) -> TimetableRepository:
    """Provide TimetableRepository via DI."""
    return TimetableRepository(session=db_session)


async def provide_timetable_service(timetable_repo: TimetableRepository) -> TimetableService:
    """Provide TimetableService via DI."""
    return TimetableService(timetable_repo=timetable_repo)


async def provide_constraint_repository(db_session: AsyncSession) -> ConstraintRepository:
    """Provide ConstraintRepository via DI."""
    return ConstraintRepository(session=db_session)


async def provide_constraint_service(
    constraint_repo: ConstraintRepository, llm_service: LLMService
) -> ConstraintService:
    """Provide ConstraintService via DI."""
    return ConstraintService(constraint_repo=constraint_repo, llm_service=llm_service)


async def provide_llm_service() -> LLMService:
    """Provide LLMService via DI."""
    return LLMService()


def create_app(database_url: str | None = None, create_all: bool = False, static_pool: bool = False) -> Litestar:
    """Create and configure the Litestar application."""
    engine_cfg = EngineConfig(poolclass=StaticPool) if static_pool else EngineConfig()
    db_config = SQLAlchemyAsyncConfig(
        connection_string=database_url or settings.database_url,
        before_send_handler=autocommit_handler_maker(commit_on_redirect=True),
        session_config=AsyncSessionConfig(expire_on_commit=False),
        engine_config=engine_cfg,
        metadata=Base.metadata,
        create_all=create_all,
        alembic_config=AlembicAsyncConfig(
            script_location=str(_BASE_DIR / "alembic"),
            render_as_batch=True,
        ),
    )

    event.listen(db_config.get_engine().sync_engine, "connect", _set_sqlite_pragmas)

    async def retrieve_user_handler(
        session: dict[str, Any],
        connection: ASGIConnection[Any, Any, Any, Any],
    ) -> User | None:
        """Reconstruct User from session-stored attributes.

        The login handler stores user_id, email, and role in the HTTP session.
        We reconstruct a transient User instance from these — no DB query needed.
        """
        user_id = session.get("user_id")
        if not user_id:
            return None
        try:
            parsed_id = uuid.UUID(user_id)
        except ValueError, AttributeError:
            await _log.awarning("invalid_session_user_id", user_id=user_id)
            return None
        email = session.get("email", "")
        role = session.get("role", "")
        if not email or not role:
            return None
        return User(id=parsed_id, email=email, hashed_password="", role=role)

    session_auth = SessionAuth[User, ServerSideSessionBackend](
        retrieve_user_handler=retrieve_user_handler,
        session_backend_config=ServerSideSessionConfig(),
        exclude=[
            "^/$",
            "^/accedi(?:\\?.*)?$",
            "^/registrati(?:\\?.*)?$",
            "^/esci(?:\\?.*)?$",
            "^/health$",
            "^/static/",
            "^/schema",
        ],
    )

    csrf_config = CSRFConfig(
        secret=settings.csrf_secret,
        cookie_name="csrftoken",
        header_name="x-csrftoken",
    )

    static_files = create_static_files_router(path="/static", directories=[_BASE_DIR / "static"])

    struct_log_config = StructLoggingConfig(
        disable_stack_trace={NotAuthorizedException},
    )
    # Route uvicorn loggers through structlog's ProcessorFormatter for consistent format
    assert struct_log_config.standard_lib_logging_config is not None
    struct_log_config.standard_lib_logging_config.loggers.update(
        {
            "uvicorn": {"level": "INFO", "handlers": ["queue_listener"], "propagate": False},
            "uvicorn.access": {"level": "INFO", "handlers": ["queue_listener"], "propagate": False},
            "uvicorn.error": {"level": "INFO", "handlers": ["queue_listener"], "propagate": False},
        }
    )
    structlog_plugin = StructlogPlugin(
        config=StructlogConfig(
            structlog_logging_config=struct_log_config,
            enable_middleware_logging=False,
        )
    )

    return Litestar(
        route_handlers=[
            HealthController,
            HomeController,
            AuthController,
            DashboardController,
            TimetableController,
            ConstraintController,
            SettingsController,
            static_files,
        ],
        plugins=[SQLAlchemyPlugin(config=db_config), structlog_plugin],
        dependencies={
            "user_repo": Provide(provide_user_repository),
            "auth_service": Provide(provide_auth_service),
            "timetable_repo": Provide(provide_timetable_repository),
            "timetable_service": Provide(provide_timetable_service),
            "constraint_repo": Provide(provide_constraint_repository),
            "constraint_service": Provide(provide_constraint_service),
            "llm_service": Provide(provide_llm_service),
        },
        on_app_init=[session_auth.on_app_init],
        exception_handlers={NotAuthorizedException: _auth_exception_handler},
        csrf_config=csrf_config,
        # TODO: Replace MemoryStore with FileStore or DB-backed store before deployment.
        # Sessions are lost on restart and partitioned across workers.
        stores={"sessions": MemoryStore()},
        template_config=TemplateConfig(
            directory=_BASE_DIR / "templates",
            engine=JinjaTemplateEngine,
        ),
        debug=settings.debug,
    )


app = create_app()
