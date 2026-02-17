"""Litestar application factory."""

import uuid
from pathlib import Path
from typing import Any

from advanced_alchemy.extensions.litestar import (
    AlembicAsyncConfig,
    AsyncSessionConfig,
    EngineConfig,
    SQLAlchemyAsyncConfig,
    SQLAlchemyPlugin,
)
from advanced_alchemy.extensions.litestar.plugins.init.config.asyncio import autocommit_handler_maker
from litestar import Litestar
from litestar.config.csrf import CSRFConfig
from litestar.connection import ASGIConnection
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.di import Provide
from litestar.logging import StructLoggingConfig
from litestar.middleware.session.server_side import ServerSideSessionBackend, ServerSideSessionConfig
from litestar.response import Redirect
from litestar.security.session_auth import SessionAuth
from litestar.static_files import create_static_files_router
from litestar.stores.memory import MemoryStore
from litestar.template.config import TemplateConfig
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.pool import StaticPool

from easyorario.config import settings
from easyorario.controllers.auth import AuthController
from easyorario.controllers.health import HealthController
from easyorario.controllers.home import HomeController
from easyorario.models.base import Base
from easyorario.models.user import User
from easyorario.repositories.user import UserRepository
from easyorario.services.auth import AuthService

_BASE_DIR = Path(__file__).resolve().parent.parent


def _set_sqlite_pragmas(dbapi_connection, connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


async def provide_user_repository(db_session: AsyncSession) -> UserRepository:
    """Provide UserRepository via DI."""
    return UserRepository(session=db_session)


async def provide_auth_service(user_repo: UserRepository) -> AuthService:
    """Provide AuthService via DI."""
    return AuthService(user_repo=user_repo)


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
        """Load user from DB using user_id stored in session.

        Uses a separate session via db_config.get_session() because this handler
        runs outside Litestar's DI context. The returned User is detached but its
        scalar attributes (id, email, role) remain accessible.
        """
        user_id = session.get("user_id")
        if not user_id:
            return None
        try:
            parsed_id = uuid.UUID(user_id)
        except (ValueError, AttributeError):
            await _log.awarning("invalid_session_user_id", user_id=user_id)
            return None
        async with db_config.get_session() as db_session:
            return await db_session.get(User, parsed_id)

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

    return Litestar(
        route_handlers=[HealthController, HomeController, AuthController, static_files],
        plugins=[SQLAlchemyPlugin(config=db_config)],
        dependencies={
            "user_repo": Provide(provide_user_repository),
            "auth_service": Provide(provide_auth_service),
        },
        on_app_init=[session_auth.on_app_init],
        exception_handlers={NotAuthorizedException: _auth_redirect_handler},
        csrf_config=csrf_config,
        # TODO: Replace MemoryStore with FileStore or DB-backed store before deployment.
        # Sessions are lost on restart and partitioned across workers.
        stores={"sessions": MemoryStore()},
        template_config=TemplateConfig(
            directory=_BASE_DIR / "templates",
            engine=JinjaTemplateEngine,
        ),
        logging_config=StructLoggingConfig(),
        debug=settings.debug,
    )


app = create_app()
