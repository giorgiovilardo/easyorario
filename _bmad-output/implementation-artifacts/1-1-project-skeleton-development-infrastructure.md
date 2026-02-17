# Story 1.1: Project Skeleton & Development Infrastructure

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want a minimal working Litestar application with development tooling,
so that I have a foundation to build features on.

## Acceptance Criteria

1. **Given** the project repository is cloned **When** I run the dev server via justfile **Then** a Litestar app starts and serves a minimal home page at `/` **And** a health check endpoint at `/health` returns 200 with a DB connectivity check (`SELECT 1`)

2. **Given** the project needs database migrations **When** I check the Alembic configuration **Then** Alembic is configured with async SQLite (WAL mode) and can run migrations **And** `alembic.ini` and `alembic/env.py` are present

3. **Given** the project needs containerization **When** I build and run the Docker image **Then** the app starts and serves requests

4. **Given** the project needs a task runner **When** I check the justfile **Then** commands exist for: dev server, tests, linting, Docker build

5. **Given** a new developer joins the project **When** they read CLAUDE.md **Then** they find modular documentation covering project structure, stack decisions, conventions, and development workflow

## Tasks / Subtasks

- [x] Task 1: Initialize project directory structure (AC: #1, #2, #4, #5)
  - [x] 1.1 Create `easyorario/` package with `__init__.py`
  - [x] 1.2 Create `easyorario/app.py` — Litestar app factory
  - [x] 1.3 Create `easyorario/config.py` — Settings from env vars
  - [x] 1.4 Create `easyorario/exceptions.py` — `EasyorarioError` base + domain exceptions
  - [x] 1.5 Create empty module directories: `controllers/`, `services/`, `models/`, `repositories/`, `guards/`, `i18n/` (each with `__init__.py`)
  - [x] 1.6 Create `templates/base.html` with Oat UI includes
  - [x] 1.7 Create `templates/pages/index.html` — minimal home page
  - [x] 1.8 Create `static/css/app.css` — empty custom CSS file
  - [x] 1.9 Include Oat UI via unpkg CDN in `templates/base.html` (no local download needed)

- [x] Task 2: Configure database with SQLAlchemy + aiosqlite (AC: #1, #2)
  - [x] 2.1 Update `pyproject.toml` dependencies: change `"litestar[standard]>=2.21.0"` to `"litestar[standard,sqlalchemy]>=2.21.0"` and add `"aiosqlite>=0.22.1"`, `"sqlalchemy>=2.0.46"` (pin explicitly for aiosqlite 0.22+ hanging thread fix)
  - [x] 2.2 Create `easyorario/models/base.py` — SQLAlchemy declarative base with common mixins
  - [x] 2.3 Configure `SQLAlchemyAsyncConfig` in app factory with `sqlite+aiosqlite:///` connection string
  - [x] 2.4 Set SQLite WAL mode via engine `"connect"` event on `engine.sync_engine`
  - [x] 2.5 Register `SQLAlchemyPlugin` with Litestar app

- [x] Task 3: Set up Alembic migrations (AC: #2)
  - [x] 3.1 Add `"alembic>=1.18.0"` to `pyproject.toml` dependencies
  - [x] 3.2 Configure `AlembicAsyncConfig` in Advanced Alchemy config with `script_location="./alembic/"`
  - [x] 3.3 Create `alembic.ini` pointing to async SQLite URL
  - [x] 3.4 Create `alembic/env.py` using async template with `render_as_batch=True` (required for SQLite ALTER TABLE)
  - [x] 3.5 Create `alembic/script.py.mako`
  - [x] 3.6 Create `alembic/versions/` directory
  - [x] 3.7 Verify `alembic check` CLI works (validated via test)

- [x] Task 4: Create health check endpoint (AC: #1)
  - [x] 4.1 Create `easyorario/controllers/health.py` with `GET /health`
  - [x] 4.2 Health check executes `SELECT 1` via async session to verify DB connectivity
  - [x] 4.3 Returns `{"status": "ok"}` on success, `{"status": "error", "error": {...}}` on failure

- [x] Task 5: Create minimal home page controller (AC: #1)
  - [x] 5.1 Create `easyorario/controllers/home.py` with `GET /`
  - [x] 5.2 Renders `templates/pages/index.html` via Jinja2 `Template` response
  - [x] 5.3 Page displays minimal Italian welcome text ("Benvenuto su Easyorario")

- [x] Task 6: Configure structlog logging (AC: #1)
  - [x] 6.1 Configure `structlog` for JSON structured logging to stdout
  - [x] 6.2 Integrate with Litestar's logging configuration

- [x] Task 7: Create justfile (AC: #4)
  - [x] 7.1 `just dev` — Start Litestar dev server with reload
  - [x] 7.2 `just test` — Run pytest
  - [x] 7.3 `just lint` — Run ruff check + pyright
  - [x] 7.4 `just fmt` — Run ruff format
  - [x] 7.5 `just docker-build` — Build Docker image
  - [x] 7.6 `just docker-run` — Run Docker container
  - [x] 7.7 `just db-migrate` — Run Alembic upgrade head
  - [x] 7.8 `just db-revision msg` — Create new Alembic revision

- [x] Task 8: Create Dockerfile (AC: #3)
  - [x] 8.1 Multi-stage Dockerfile: build stage (install deps) + runtime stage
  - [x] 8.2 Use Python 3.14 base image
  - [x] 8.3 Mount point for SQLite database volume
  - [x] 8.4 Expose port and run Litestar via uvicorn

- [x] Task 9: Create configuration and env files (AC: #1)
  - [x] 9.1 Create `.env.example` with `SECRET_KEY`, `DATABASE_URL`
  - [x] 9.2 Update `.gitignore` for Python, SQLite, .env, __pycache__, .venv
  - [x] 9.3 Create `easyorario/config.py` loading settings from environment

- [x] Task 10: Create CLAUDE.md project documentation (AC: #5)
  - [x] 10.1 Project overview and stack summary
  - [x] 10.2 Directory structure reference
  - [x] 10.3 Development workflow (TDD, jj VCS commands)
  - [x] 10.4 Conventions (naming, patterns, anti-patterns)
  - [x] 10.5 Quick start guide (setup, dev server, tests)

- [x] Task 11: Write tests (AC: #1, #2, #4)
  - [x] 11.1 Create `tests/conftest.py` with test client fixture, test DB (in-memory SQLite)
  - [x] 11.2 Test: `GET /` returns 200 with Italian welcome text
  - [x] 11.3 Test: `GET /health` returns 200 with `{"status": "ok"}`
  - [x] 11.4 Test: Alembic migrations can run successfully
  - [x] 11.5 Test: SQLite WAL mode is active

## Dev Notes

### Architecture Patterns & Constraints

- **Layered architecture:** Controller → Service → Repository with one-way dependencies. Controllers handle HTTP, services contain business logic, repositories handle data access.
- **App factory pattern:** `easyorario/app.py` creates and configures the Litestar app instance with all plugins, middleware, and route handlers.
- **Custom exception hierarchy:** `EasyorarioError` base class in `exceptions.py`. Domain exceptions: `UnsolvableConstraintsError`, `LLMTranslationError`, `ConstraintConflictError`. For this story, only the base `EasyorarioError` is needed.
- **Error handling:** Litestar exception handlers render Italian error templates. `structlog` for server-side logging. Never use `print()`.
- **No camelCase:** All Python code, JSON fields use `snake_case`. URLs use `kebab-case`.

### Technical Stack (Exact Versions)

| Technology | Version | Notes |
|---|---|---|
| Python | >=3.14 | Type checking via Pyright |
| Litestar | >=2.21.0 | Use `litestar[standard,sqlalchemy]` for Jinja2 + Advanced Alchemy |
| SQLAlchemy | >=2.0.46 | **Critical**: Must be >=2.0.46 for aiosqlite 0.22+ hanging thread fix. Pin explicitly. |
| aiosqlite | >=0.22.1 | Async SQLite driver |
| Advanced Alchemy | latest (transitive via litestar[sqlalchemy]) | `advanced_alchemy.extensions.litestar` for SQLAlchemy plugin |
| Alembic | >=1.18.0 | Async migrations via `alembic init -t async` template pattern |
| structlog | >=25.5.0 | JSON structured logging to stdout |
| Z3 Solver | >=4.15.8.0 | Already in pyproject.toml (not used in this story) |
| Oat UI | latest via unpkg CDN (@knadh/oat) | ~8KB CSS + ~2KB JS. Semantic HTML-first. |
| Ruff | >=0.15.1 | Linting + formatting |
| Pyright | >=1.1.408 | Type checking |
| pytest | >=9.0.2 | Testing |
| pytest-asyncio | >=1.3.0 | Async test support |
| just | system-installed | Task runner |
| Docker | system-installed | Containerization |

### Litestar Configuration Details

**Advanced Alchemy setup:**
```python
from advanced_alchemy.extensions.litestar import (
    AsyncSessionConfig,
    SQLAlchemyAsyncConfig,
    SQLAlchemyPlugin,
    AlembicAsyncConfig,
)

session_config = AsyncSessionConfig(expire_on_commit=False)
alchemy_config = SQLAlchemyAsyncConfig(
    connection_string="sqlite+aiosqlite:///app.db",
    before_send_handler="autocommit",
    session_config=session_config,
    alembic_config=AlembicAsyncConfig(script_location="./alembic/"),
)
```

**SQLite WAL mode (engine event):**
```python
from sqlalchemy import event

@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
```

**Jinja2 templating:**
```python
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.response import Template
from litestar.template.config import TemplateConfig

template_config = TemplateConfig(
    directory=Path("templates"),
    engine=JinjaTemplateEngine,
)
```

**Jinja2 import:** Use `from litestar.contrib.jinja import JinjaTemplateEngine`. This is the canonical import path as of Litestar 2.21.0.

### Alembic Configuration

- **Must use `render_as_batch=True`** in `context.configure()` — SQLite has limited ALTER TABLE support; batch mode recreates tables.
- **Async env.py pattern:** Uses `async_engine_from_config` + `connection.run_sync(do_run_migrations)`.
- **Advanced Alchemy CLI:** `litestar database make-migrations`, `litestar database upgrade`, etc.
- **Migration naming:** Descriptive slugs (e.g., `create_users_table`).

### Oat UI Integration

- Include via unpkg CDN in `templates/base.html`:
  - `<link rel="stylesheet" href="https://unpkg.com/@knadh/oat/oat.min.css">`
  - `<script src="https://unpkg.com/@knadh/oat/oat.min.js" defer></script>`
- No local download needed — served from CDN
- Semantic HTML-first: style native elements directly, no class soup
- CSS variables for theming (override in `app.css` if needed)
- Dark mode: `data-theme="dark"` on `<body>`
- Web components for: tabs, dropdowns, dialogs

### Version Control

- **Prefer `jj` (Jujutsu)** for VCS operations — `jj new`, `jj describe -m "message"`, `jj commit`
- View history: `jj log` / View changes: `jj diff`
- **If `jj` is not available** in the execution environment, use `git` with equivalent commands. The preference for `jj` applies to human developers; AI dev agents may use `git` directly if `jj` is not installed.

### TDD Workflow (Mandatory)

1. **Red:** Write a small, focused test that fails. Test names: `test_{action}_{condition}_{expected_result}`
2. **Green:** Write minimum code to make test pass
3. **Refactor/Tidy:** Clean up only if needed. All tests must stay green.
4. **Repeat.**

Rules:
- Never write production code without a failing test first
- Never write more than one failing test at a time
- Commit after each meaningful green-refactor cycle

**TDD scope for this story:** Tasks 1-3, 6-10 create configuration/infrastructure files that are not directly testable in isolation. Apply TDD to Tasks 4, 5, and 11:
- Write the health check test (11.3) BEFORE implementing health.py (Task 4)
- Write the home page test (11.2) BEFORE implementing home.py (Task 5)
- Write the DB/WAL tests (11.4, 11.5) BEFORE the DB configuration is verified

For infrastructure tasks, verify correctness via the integration tests in Task 11 and manual smoke testing (`just dev`, `just docker-build`).

**Execution order:** Infrastructure tasks (1-3, 6-10) first, then TDD cycle for features (4, 5 with tests from 11).

### Project Structure Notes

Target directory structure for this story:

```
easyorario/
├── pyproject.toml              (UPDATE: litestar[standard,sqlalchemy], aiosqlite>=0.22.1, sqlalchemy>=2.0.46, alembic>=1.18.0)
├── justfile                    (CREATE)
├── Dockerfile                  (CREATE)
├── .env.example                (CREATE)
├── .gitignore                  (UPDATE)
├── CLAUDE.md                   (CREATE)
├── alembic.ini                 (CREATE)
├── alembic/
│   ├── env.py                  (CREATE)
│   ├── script.py.mako          (CREATE)
│   └── versions/               (CREATE)
├── src/
│   └── easyorario/
│       ├── __init__.py         (CREATE)
│       ├── app.py              (CREATE)
│       ├── config.py           (CREATE)
│       ├── exceptions.py       (CREATE)
│       ├── controllers/
│       │   ├── __init__.py     (CREATE)
│       │   ├── health.py       (CREATE)
│       │   └── home.py         (CREATE)
│       ├── services/
│       │   └── __init__.py     (CREATE)
│       ├── models/
│       │   ├── __init__.py     (CREATE)
│       │   └── base.py         (CREATE)
│       ├── repositories/
│       │   └── __init__.py     (CREATE)
│       ├── guards/
│       │   └── __init__.py     (CREATE)
│       └── i18n/
│           └── __init__.py     (CREATE)
├── templates/
│   ├── base.html               (CREATE)
│   └── pages/
│       └── index.html          (CREATE)
├── static/
│   ├── css/
│   │   └── app.css             (CREATE — empty)
│   └── js/
├── tests/
│   ├── conftest.py             (CREATE)
│   ├── controllers/
│   │   ├── test_health.py      (CREATE)
│   │   └── test_home.py        (CREATE)
│   └── models/
│       └── test_db.py          (CREATE — WAL mode, migration tests)
└── docs/
    └── PRD.md                  (EXISTS)
```

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure & Boundaries]
- [Source: _bmad-output/planning-artifacts/architecture.md#Core Architectural Decisions]
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns & Consistency Rules]
- [Source: _bmad-output/planning-artifacts/architecture.md#Starter Template Evaluation]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.1]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Design System]
- [Source: docs/PRD.md#Functional Requirements]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

- Fixed `ModuleNotFoundError` for `easyorario` in pytest by adding `pythonpath = ["src"]` to `[tool.pytest.ini_options]`
- Fixed same issue in Alembic by adding `sys.path.insert` in `alembic/env.py`
- Fixed Litestar `StaticFilesConfig` deprecation warning by switching to `create_static_files_router`
- Removed `from __future__ import annotations` per user preference (Python 3.14+ native syntax)
- Dropped `TCH` ruff rule set — incompatible with Litestar DI patterns that require runtime type imports

### Completion Notes List

- Created full `easyorario/` package with layered architecture directories (controllers, services, models, repositories, guards, i18n)
- Configured SQLAlchemy async with aiosqlite, WAL mode pragmas via engine connect event, Advanced Alchemy plugin
- Set up Alembic with async env.py, batch mode for SQLite, and script.py.mako template
- Created health check endpoint (`GET /health`) with DB connectivity verification via `SELECT 1`
- Created home page controller (`GET /`) rendering Italian welcome template
- Configured structlog via Litestar's `StructLoggingConfig` integration
- Created justfile with all 8 required commands (dev, test, lint, fmt, docker-build, docker-run, db-migrate, db-revision)
- Created multi-stage Dockerfile with Python 3.14, uv for deps, SQLite volume mount
- Created `.env.example`, updated `.gitignore`, `config.py` with environment-based settings
- CLAUDE.md already existed and was updated with "no `from __future__ import annotations`" rule
- 4 tests: home page 200, health check 200, SQLite WAL mode, Alembic configuration validity
- All tests pass, ruff check + format clean

### Change Log

- 2026-02-17: Initial implementation of project skeleton and development infrastructure (all 11 tasks)
- 2026-02-17: Adversarial review fixes — app factory pattern, in-memory test DB, health check 503, class-level SQLite pragmas, alembic env override, dotenv via justfile, flat layout consistency, removed unused UUIDBase

### File List

- pyproject.toml (MODIFIED — added dependencies, pytest/ruff/pyright config)
- CLAUDE.md (MODIFIED — added `from __future__` ban rule)
- .gitignore (MODIFIED — added .env, SQLite, alembic patterns)
- justfile (CREATED)
- Dockerfile (CREATED)
- .env.example (CREATED)
- alembic.ini (CREATED)
- alembic/env.py (CREATED)
- alembic/script.py.mako (CREATED)
- alembic/versions/ (CREATED — empty)
- easyorario/__init__.py (CREATED)
- easyorario/app.py (CREATED)
- easyorario/config.py (CREATED)
- easyorario/exceptions.py (CREATED)
- easyorario/controllers/__init__.py (CREATED)
- easyorario/controllers/health.py (CREATED)
- easyorario/controllers/home.py (CREATED)
- easyorario/services/__init__.py (CREATED)
- easyorario/models/__init__.py (CREATED)
- easyorario/models/base.py (CREATED)
- easyorario/repositories/__init__.py (CREATED)
- easyorario/guards/__init__.py (CREATED)
- easyorario/i18n/__init__.py (CREATED)
- templates/base.html (CREATED)
- templates/pages/index.html (CREATED)
- static/css/app.css (CREATED — empty)
- tests/__init__.py (CREATED)
- tests/conftest.py (CREATED)
- tests/controllers/__init__.py (CREATED)
- tests/controllers/test_health.py (CREATED)
- tests/controllers/test_home.py (CREATED)
- tests/models/__init__.py (CREATED)
- tests/models/test_db.py (CREATED)
