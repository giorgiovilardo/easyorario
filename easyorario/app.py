"""Litestar application factory."""

from pathlib import Path

from advanced_alchemy.extensions.litestar import (
    AlembicAsyncConfig,
    AsyncSessionConfig,
    SQLAlchemyAsyncConfig,
    SQLAlchemyPlugin,
)
from litestar import Litestar
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.logging import StructLoggingConfig
from litestar.static_files import create_static_files_router
from litestar.template.config import TemplateConfig
from sqlalchemy import event
from sqlalchemy.engine import Engine

from easyorario.config import settings
from easyorario.controllers.health import HealthController
from easyorario.controllers.home import HomeController

_BASE_DIR = Path(__file__).resolve().parent.parent


@event.listens_for(Engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def create_app(database_url: str | None = None) -> Litestar:
    """Create and configure the Litestar application."""
    db_config = SQLAlchemyAsyncConfig(
        connection_string=database_url or settings.database_url,
        before_send_handler="autocommit",
        session_config=AsyncSessionConfig(expire_on_commit=False),
        alembic_config=AlembicAsyncConfig(
            script_location=str(_BASE_DIR / "alembic"),
            render_as_batch=True,
        ),
    )

    static_files = create_static_files_router(path="/static", directories=[_BASE_DIR / "static"])

    return Litestar(
        route_handlers=[HealthController, HomeController, static_files],
        plugins=[SQLAlchemyPlugin(config=db_config)],
        template_config=TemplateConfig(
            directory=_BASE_DIR / "templates",
            engine=JinjaTemplateEngine,
        ),
        logging_config=StructLoggingConfig(),
        debug=settings.debug,
    )


app = create_app()
