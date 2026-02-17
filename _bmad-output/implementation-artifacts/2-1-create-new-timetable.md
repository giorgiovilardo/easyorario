# Story 2.1: Create New Timetable

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a Responsible Professor,
I want to create a new timetable by entering class information,
so that I have a timetable workspace to define scheduling constraints.

## Acceptance Criteria

1. **Given** I am logged in as a Responsible Professor on `/dashboard` **When** I click "Nuovo Orario" **Then** I am taken to `/orario/nuovo`

2. **Given** I am on the create timetable page (`/orario/nuovo`) **When** I submit class identifier (e.g., "3A Liceo Scientifico"), school year (e.g., "2026/2027"), number of weekly hours (e.g., 30), subject list, and teacher assignments **Then** a Timetable is created with status "draft" and I am redirected to `/orario/{id}/vincoli`

3. **Given** the Timetable model needs to be persisted **When** I check the database **Then** a `timetables` table exists with columns: id (UUID PK), class_identifier, school_year, weekly_hours, subjects (JSON), teachers (JSON), status, owner_id (FK to users.id), created_at **And** an Alembic migration was created for this table

4. **Given** I am a Professor (not Responsible Professor) **When** I try to access `/orario/nuovo` **Then** I receive a 403 Forbidden response

5. **Given** I submit the form with missing required fields (empty class_identifier or weekly_hours < 1) **When** the form is processed **Then** I see an Italian validation error and remain on the form page

## Tasks / Subtasks

- [x] Task 1: Create Timetable model and Alembic migration (AC: #3)
  - [x] 1.1 Create `easyorario/models/timetable.py` — Timetable ORM model with UUID PK, class_identifier (String), school_year (String), weekly_hours (Integer), subjects (JSON), teachers (JSON), status (String, default "draft"), owner_id (FK → users.id), created_at
  - [x] 1.2 Add relationship: `Timetable.owner` → User, `User.timetables` → list[Timetable]
  - [x] 1.3 Export Timetable from `easyorario/models/__init__.py`
  - [x] 1.4 Generate Alembic migration: `just db-revision "create timetables table"`
  - [x] 1.5 Verify migration applies cleanly: `just db-migrate`

- [x] Task 2: Create TimetableRepository (AC: #2, #3)
  - [x] 2.1 Create `easyorario/repositories/timetable.py` — TimetableRepository extending `SQLAlchemyAsyncRepository[Timetable]`
  - [x] 2.2 Add `get_by_owner(owner_id: uuid.UUID) -> list[Timetable]` method for future dashboard use
  - [x] 2.3 Export from `easyorario/repositories/__init__.py`

- [x] Task 3: Create TimetableService (AC: #2, #5)
  - [x] 3.1 Create `easyorario/services/timetable.py` — TimetableService with `create_timetable()` method
  - [x] 3.2 Validate required fields: class_identifier non-empty, weekly_hours ≥ 1, school_year non-empty
  - [x] 3.3 Accept subjects as list of strings, teachers as dict mapping subject → teacher name
  - [x] 3.4 Set status="draft", owner_id from authenticated user
  - [x] 3.5 Return created Timetable

- [x] Task 4: Add domain exceptions and Italian messages (AC: #5)
  - [x] 4.1 Add `InvalidTimetableDataError` to `easyorario/exceptions.py` with error_key
  - [x] 4.2 Add Italian validation messages to `easyorario/i18n/errors.py`

- [x] Task 5: Update TimetableController with create form + POST handler (AC: #1, #2, #4, #5)
  - [x] 5.1 Replace stub `GET /orario/nuovo` with form rendering (keep `requires_responsible_professor` guard)
  - [x] 5.2 Add `POST /orario/nuovo` — parse form data, call TimetableService, redirect to `/orario/{id}/vincoli`
  - [x] 5.3 On validation error: re-render form with Italian error message and submitted values
  - [x] 5.4 Add stub `GET /orario/{timetable_id:uuid}/vincoli` route returning placeholder template (for redirect target)

- [x] Task 6: Create timetable form template (AC: #1, #2, #5)
  - [x] 6.1 Replace `templates/pages/timetable_new.html` with create timetable form
  - [x] 6.2 Fields: class_identifier (text input), school_year (text input), weekly_hours (number input), subjects (textarea, one per line), teachers (textarea, format "Materia: Prof. Nome" per line)
  - [x] 6.3 All labels and placeholders in Italian
  - [x] 6.4 Use Oat UI form styling, CSRF token included
  - [x] 6.5 Create `templates/pages/timetable_constraints.html` stub (placeholder for redirect target)

- [x] Task 7: Register DI providers in app.py (AC: #2)
  - [x] 7.1 Add `provide_timetable_repository` and `provide_timetable_service` DI functions
  - [x] 7.2 Register in `dependencies` dict in `create_app()`

- [x] Task 8: Write tests (AC: #1, #2, #3, #4, #5)
  - [x] 8.1 `tests/models/test_timetable.py`: model creation and field defaults
  - [x] 8.2 `tests/repositories/test_timetable_repository.py`: CRUD and get_by_owner
  - [x] 8.3 `tests/services/test_timetable.py`: create_timetable validation and happy path
  - [x] 8.4 `tests/controllers/test_timetable.py`: GET form, POST create, validation errors, 403 for Professor, redirect to vincoli

## Dev Notes

### Architecture Patterns & Constraints

- **Layered architecture applies fully:** TimetableController (HTTP) → TimetableService (business logic) → TimetableRepository (data access) → SQLite. One-way dependency — never reversed.
- **Dependency injection:** Use Litestar's DI. Inject `TimetableService` into the controller; inject `TimetableRepository` into the service. Follow the existing pattern in `app.py` with `provide_user_repository` / `provide_auth_service`.
- **Guards enforce authorization declaratively:** The `requires_responsible_professor` guard from `guards/auth.py` is already applied to the stub `GET /orario/nuovo`. Keep it and apply it to the new `POST /orario/nuovo` as well.
- **Italian-only user-facing text:** All form labels, placeholders, validation errors, and page text in Italian. Code and logs in English.
- **No Constraint or Revision models yet:** Only the Timetable model is created in this story. Constraints (Epic 2 Story 2.2) and Revisions (Epic 4) come later.
- **`/orario/{id}/vincoli` is a stub redirect target:** Story 2.2 implements the full constraints page. This story only needs a placeholder route + template so the POST-redirect-GET cycle works.

### Timetable Data Model Design

The epics specify subjects as JSON and teachers as JSON. The design decision:

- **`subjects`**: `list[str]` stored as JSON column — e.g., `["Matematica", "Italiano", "Fisica"]`
- **`teachers`**: `dict[str, str]` stored as JSON column — maps subject to teacher name, e.g., `{"Matematica": "Prof. Rossi", "Italiano": "Prof. Bianchi"}`
- **`weekly_hours`**: `int` — total weekly hours for the class (typically 27-32 for Italian schools)
- **`school_year`**: `str` — e.g., "2026/2027" (free-form, not validated beyond non-empty)
- **`class_identifier`**: `str` — e.g., "3A Liceo Scientifico" (free-form, max 255 chars)
- **`status`**: `str` — "draft" initially. Later statuses: "final" (Epic 5). Do NOT use an enum for this — keep it as a string column to avoid migration headaches when new statuses are added.

**Foreign key:** `owner_id` → `users.id` (UUID). The owner is the Responsible Professor who created the timetable. Use `ForeignKey("users.id")` with `ondelete="CASCADE"`.

### Form Input Parsing

The form uses plain HTML inputs. Subjects and teachers need server-side parsing:

**Subjects textarea** — one subject per line:
```
Matematica
Italiano
Fisica
Storia
```
→ Parse: `[line.strip() for line in text.splitlines() if line.strip()]`

**Teachers textarea** — "Subject: Teacher Name" per line:
```
Matematica: Prof. Rossi
Italiano: Prof. Bianchi
Fisica: Prof. Verdi
```
→ Parse: split each line on first `:`, strip both parts, build dict. Lines without `:` or with empty parts are validation errors.

**Validation rules in TimetableService:**
- `class_identifier`: non-empty after strip, max 255 chars
- `school_year`: non-empty after strip
- `weekly_hours`: integer ≥ 1 and ≤ 60 (reasonable upper bound)
- `subjects`: at least 1 subject after parsing
- `teachers`: optional (can be empty dict — not all subjects need teachers assigned at creation time)

### SessionAuth & User Access Pattern

The `request.user` is a `User` model instance, populated by `retrieve_user_handler` in `app.py`. On protected routes (not in `exclude` list), it is guaranteed non-None. Use `request.user.id` as `owner_id` when creating a timetable.

```python
@post("/nuovo", guards=[requires_responsible_professor])
async def create_timetable(
    self,
    request: Request,
    data: Annotated[dict[str, str], Body(media_type=RequestEncodingType.URL_ENCODED)],
    timetable_service: TimetableService,
) -> Redirect:
    timetable = await timetable_service.create_timetable(
        owner_id=request.user.id,
        class_identifier=data.get("class_identifier", ""),
        school_year=data.get("school_year", ""),
        weekly_hours_raw=data.get("weekly_hours", ""),
        subjects_raw=data.get("subjects", ""),
        teachers_raw=data.get("teachers", ""),
    )
    return Redirect(path=f"/orario/{timetable.id}/vincoli")
```

### Architecture Compliance

**Boundary Rules — MUST follow:**

| Rule | This Story's Application |
|---|---|
| Controller → Service → Repository (one-way) | TimetableController calls TimetableService; TimetableService calls TimetableRepository. Controller NEVER touches repository directly. |
| Controllers handle HTTP only — no business logic | Controller parses form data, passes raw strings to service. Service validates, parses subjects/teachers, creates model. |
| Guards enforce authorization declaratively | `requires_responsible_professor` guard on both GET and POST `/orario/nuovo`. |
| Italian user-facing text, English code/logs | Template text in Italian. Python identifiers, comments, log messages in English. |
| `structlog` for all logging, never `print()` | Log timetable creation events: `await _log.ainfo("timetable_created", timetable_id=str(t.id), owner=str(owner_id))` |
| Use Litestar DI, never manual instantiation | TimetableRepository and TimetableService provided via Litestar's `Provide` / type-hint DI. |
| `snake_case` for Python/JSON, `kebab-case` for URLs | Table: `timetables`. Columns: `class_identifier`, `weekly_hours`, `owner_id`. URL: `/orario/nuovo`. |
| `jj` for VCS, never raw `git` | All commits via `jj commit -m "message"`. |

**Anti-Patterns — NEVER do:**

- Do NOT hardcode Italian strings in Python code — use templates or `i18n/errors.py` message mappings
- Do NOT check `request.user.role` in the controller for access control — guards handle it
- Do NOT create Constraint, Revision, or Comment models in this story
- Do NOT add complex JavaScript — the form is a standard HTML form POST
- Do NOT use bare `except:` or catch `Exception` without re-raising
- Do NOT use `git` commands — use `jj` exclusively
- Do NOT add `from __future__ import annotations` — Python 3.14+, not needed

### Library & Framework Requirements

**Litestar (>=2.21.0) — Key APIs for this story:**

| API | Usage | Import |
|---|---|---|
| `Request.user` | Access authenticated User instance | `from litestar import Request` |
| `Template` | Render Jinja2 template response | `from litestar.response import Template` |
| `Redirect` | HTTP redirect after create | `from litestar.response import Redirect` |
| `Controller` | Base class for route controllers | `from litestar import Controller` |
| `get`, `post` | Route decorators | `from litestar import get, post` |
| `Body` | Parse form-encoded POST data | `from litestar.params import Body` |
| `RequestEncodingType` | Specify URL-encoded form | `from litestar.enums import RequestEncodingType` |
| `guards` | Route-level guard list | Route decorator param |
| `Provide` | DI provider registration | `from litestar.di import Provide` |

**Litestar form data parsing:**

To receive HTML form POST data, use `Body(media_type=RequestEncodingType.URL_ENCODED)`:

```python
from typing import Annotated
from litestar.params import Body
from litestar.enums import RequestEncodingType

@post("/nuovo", guards=[requires_responsible_professor])
async def create_timetable(
    self,
    request: Request,
    data: Annotated[dict[str, str], Body(media_type=RequestEncodingType.URL_ENCODED)],
    timetable_service: TimetableService,
) -> Template | Redirect:
    ...
```

**SQLAlchemy — JSON column for subjects/teachers:**

```python
from sqlalchemy import JSON, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

class Timetable(Base):
    __tablename__ = "timetables"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    class_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    school_year: Mapped[str] = mapped_column(String(20), nullable=False)
    weekly_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    subjects: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    teachers: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    owner: Mapped["User"] = relationship(back_populates="timetables", lazy="selectin")
```

**Advanced Alchemy — Repository pattern:**

```python
from advanced_alchemy.repository import SQLAlchemyAsyncRepository

class TimetableRepository(SQLAlchemyAsyncRepository[Timetable]):
    model_type = Timetable
```

The base class provides `add()`, `get()`, `list()`, `delete()` etc. Only add custom query methods as needed.

**Alembic — Migration generation:**

```bash
just db-revision "create timetables table"
```

This runs `alembic revision --autogenerate -m "create timetables table"`. The migration will detect the new Timetable model via `Base.metadata`. Ensure the model is imported in `alembic/env.py` (it should auto-discover via `Base`).

**Oat UI — Form elements used:**

| Element | HTML | Usage |
|---|---|---|
| Text input | `<input type="text">` | class_identifier, school_year |
| Number input | `<input type="number" min="1">` | weekly_hours |
| Textarea | `<textarea>` | subjects (one per line), teachers (subject: teacher per line) |
| Button | `<button type="submit">` | "Crea Orario" submit button |
| Alert | `<div role="alert">` | Validation error display |
| Form | `<form method="post">` | Standard HTML form with CSRF |

**No new dependencies required.** Everything needed is already in `pyproject.toml`.

### File Structure Requirements

**Files to CREATE:**

```
easyorario/models/timetable.py                   (CREATE: Timetable ORM model)
easyorario/repositories/timetable.py              (CREATE: TimetableRepository)
easyorario/services/timetable.py                  (CREATE: TimetableService)
templates/pages/timetable_constraints.html         (CREATE: stub placeholder for /orario/{id}/vincoli)
tests/models/test_timetable.py                     (CREATE: model tests)
tests/repositories/test_timetable_repository.py    (CREATE: repository tests)
tests/services/test_timetable.py                   (CREATE: service tests)
tests/controllers/test_timetable.py                (CREATE: controller integration tests)
alembic/versions/*_create_timetables_table.py      (CREATE: auto-generated migration)
```

**Files to UPDATE:**

```
easyorario/models/__init__.py                      (UPDATE: export Timetable)
easyorario/repositories/__init__.py                (UPDATE: export TimetableRepository)
easyorario/controllers/timetable.py                (UPDATE: replace stub with full create form + POST handler + vincoli stub)
easyorario/app.py                                  (UPDATE: add TimetableRepository and TimetableService DI providers)
easyorario/exceptions.py                           (UPDATE: add InvalidTimetableDataError)
easyorario/i18n/errors.py                          (UPDATE: add timetable validation messages)
templates/pages/timetable_new.html                 (UPDATE: replace stub with create form)
```

**Files NOT to touch:**

```
easyorario/models/user.py                          (NO CHANGE — only add back_populates="timetables" relationship if needed, but prefer adding it in timetable.py via string reference)
easyorario/services/auth.py                        (NO CHANGE)
easyorario/controllers/auth.py                     (NO CHANGE)
easyorario/controllers/dashboard.py                (NO CHANGE — dashboard timetable listing is a separate concern, future task)
easyorario/guards/auth.py                          (NO CHANGE — requires_responsible_professor already exists)
templates/base.html                                (NO CHANGE)
templates/pages/dashboard.html                     (NO CHANGE — "Nuovo Orario" button already links to /orario/nuovo)
```

**Note on User model relationship:** Adding `timetables` relationship to User requires modifying `user.py`. If using string-based lazy relationship references, you can define only the Timetable side. Prefer the simpler approach: define `relationship` only on Timetable model with `back_populates`, and add the reverse on User model. This is a minimal change.

### Testing Requirements

**TDD Workflow — Mandatory:**

1. **Red:** Write a small, focused test that fails
2. **Green:** Write minimum code to make it pass
3. **Refactor/Tidy:** Clean up only if needed, all tests stay green
4. **Repeat**

Test naming: `test_{action}_{condition}_{expected_result}`

**Test Fixtures Needed:**

Reuse existing fixtures from `tests/conftest.py`:
- `client` — AsyncTestClient with in-memory DB
- `db_session` — standalone async session for model/repo tests
- `registered_user` / `authenticated_client` — logged-in Responsible Professor
- `professor_user` / `authenticated_professor_client` — logged-in Professor

New fixture needed:
```python
@pytest.fixture
async def timetable_data() -> dict[str, str]:
    """Valid form data for creating a timetable."""
    return {
        "class_identifier": "3A Liceo Scientifico",
        "school_year": "2026/2027",
        "weekly_hours": "30",
        "subjects": "Matematica\nItaliano\nFisica\nStoria",
        "teachers": "Matematica: Prof. Rossi\nItaliano: Prof. Bianchi",
    }
```

**Required Test Cases:**

| Test File | Test Name | Verifies |
|---|---|---|
| `test_timetable.py` (model) | `test_create_timetable_model_has_correct_defaults` | status="draft", created_at set |
| `test_timetable.py` (model) | `test_timetable_owner_relationship_links_to_user` | FK relationship works |
| `test_timetable_repository.py` | `test_add_timetable_persists_to_database` | Basic CRUD |
| `test_timetable_repository.py` | `test_get_by_owner_returns_only_owned_timetables` | Owner filtering |
| `test_timetable.py` (service) | `test_create_timetable_with_valid_data_returns_draft` | Happy path: creates with status=draft |
| `test_timetable.py` (service) | `test_create_timetable_with_empty_class_identifier_raises` | Validation: class_identifier required |
| `test_timetable.py` (service) | `test_create_timetable_with_zero_weekly_hours_raises` | Validation: weekly_hours >= 1 |
| `test_timetable.py` (service) | `test_create_timetable_with_empty_school_year_raises` | Validation: school_year required |
| `test_timetable.py` (service) | `test_create_timetable_with_no_subjects_raises` | Validation: at least 1 subject |
| `test_timetable.py` (controller) | `test_get_nuovo_as_responsible_professor_returns_form` | AC #1: form renders |
| `test_timetable.py` (controller) | `test_get_nuovo_as_professor_returns_403` | AC #4: guard blocks |
| `test_timetable.py` (controller) | `test_post_nuovo_with_valid_data_creates_timetable_and_redirects` | AC #2: create + redirect to vincoli |
| `test_timetable.py` (controller) | `test_post_nuovo_with_empty_class_identifier_shows_error` | AC #5: validation error |
| `test_timetable.py` (controller) | `test_post_nuovo_with_invalid_weekly_hours_shows_error` | AC #5: validation error |
| `test_timetable.py` (controller) | `test_get_vincoli_stub_returns_placeholder` | Redirect target works |

**Testing the create flow (integration):**

```python
async def test_post_nuovo_with_valid_data_creates_timetable_and_redirects(
    authenticated_client, timetable_data,
):
    csrf_token = _get_csrf_token(authenticated_client)
    response = await authenticated_client.post(
        "/orario/nuovo",
        data={**timetable_data, "_csrf_token": csrf_token},
        follow_redirects=False,
    )
    assert response.status_code == 302  # or 301
    assert "/orario/" in response.headers["location"]
    assert "/vincoli" in response.headers["location"]
```

**In-memory SQLite test DB pattern:**

Tests use `create_all=True` + `StaticPool` (from `conftest.py`). The new Timetable model will be auto-created via `Base.metadata.create_all`. No migration needed for tests — tests use the ORM models directly.

### Previous Story Intelligence

**From Story 1.4 (Dashboard & Role-Based Access Control) — Direct predecessor:**

- **`TimetableController` stub exists** at `easyorario/controllers/timetable.py` with `path = "/orario"` and single `GET /nuovo` route guarded by `requires_responsible_professor`. This story replaces the stub with full implementation.
- **`templates/pages/timetable_new.html` exists** as a placeholder ("Questa funzionalità sarà disponibile presto"). Replace with the actual form.
- **Dashboard "Nuovo Orario" button** already links to `/orario/nuovo` — no dashboard changes needed.
- **Auth exception handler** distinguishes 401 (redirect to `/accedi`) from 403 (Italian error page) via `request.scope.get("user")`. This pattern applies to the new POST route too.
- **`requires_responsible_professor` guard** is defined in `guards/auth.py`. Reuse as-is.
- **Test fixtures**: `authenticated_client` (RP), `authenticated_professor_client` (Prof), `_get_csrf_token()` helper — all reusable.

**Key pattern from 1.4 dev notes:**
- `request.user` raises `KeyError`, not `AttributeError` when user not in scope — use `request.scope.get("user")` in exception handlers.
- `autocommit_handler_maker(commit_on_redirect=True)` is configured — the redirect after POST will auto-commit the session, so the new timetable will be persisted before the redirect completes.

**From Story 1.2 (User Registration):**
- **CSRF middleware** is active — all POST forms must include `{{ csrf_input | safe }}` hidden input.
- **Service pattern**: `AuthService.__init__(self, user_repo)` — follow this for `TimetableService.__init__(self, timetable_repo)`.
- **Exception pattern**: Custom exceptions with `error_key` attribute → mapped to Italian messages in `i18n/errors.py`.

**From Story 1.1 (Project Skeleton):**
- **Alembic configured** with `render_as_batch=True` for SQLite compatibility.
- **`conftest.py`** pattern: `create_app(database_url="sqlite+aiosqlite://", create_all=True, static_pool=True)`.

### Git Intelligence

**Recent commits show:**
```
b0e95b2 unify log format: route uvicorn loggers through structlog via StructlogPlugin
1a4272e suppress noisy NotAuthorizedException stack traces in debug logging
026bbbc fix code review findings: structlog logging, top-level imports, conditional nav logo
3ae718e story 1.4: finalize — update story status to review, CLAUDE.md, justfile check recipe
6e65a20 story 1.4: comprehensive tests for dashboard, guards, error handlers (task 8)
```

**Patterns to follow:**
- Atomic commits per task/subtask group (e.g., "story 2.1: timetable model and migration (task 1)")
- `just check` before every commit (format + lint + typecheck)
- structlog for all logging with descriptive event names
- Top-level imports preferred over lazy imports

**Code conventions observed:**
- Controllers are thin — delegate to services
- Services use structlog `_log = structlog.get_logger()` at module level
- Repositories extend `SQLAlchemyAsyncRepository[Model]` with minimal custom methods
- Tests use `_get_csrf_token()` helper for CSRF-protected POST requests

### Project Structure Notes

- **Flat layout confirmed:** `easyorario/` at project root (no `src/`). The architecture doc mentions `src/easyorario/` but the actual project uses `easyorario/` directly. Follow what exists, not the architecture doc.
- **Tests at `tests/`** at project root, mirroring `easyorario/` structure.
- **Templates at `templates/`** at project root.
- **Static at `static/`** at project root.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.1]
- [Source: _bmad-output/planning-artifacts/architecture.md#Data Architecture]
- [Source: _bmad-output/planning-artifacts/architecture.md#Authentication & Security]
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns & Consistency Rules]
- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure & Boundaries]
- [Source: _bmad-output/planning-artifacts/architecture.md#Architectural Boundaries]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Page Map & User Journeys]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Key Interaction Patterns]
- [Source: _bmad-output/implementation-artifacts/1-4-dashboard-role-based-access-control.md]
- [Source: CLAUDE.md#Architecture]
- [Source: CLAUDE.md#Commands]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
