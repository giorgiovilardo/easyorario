# Story 2.2: Constraint Input in Natural Language

Status: ready-for-dev

## Story

As a Responsible Professor,
I want to input scheduling constraints in Italian natural language,
so that I can define the rules for timetable generation without technical syntax.

## Acceptance Criteria

1. **Given** I am on `/orario/{id}/vincoli` for my timetable **When** I type an Italian constraint in the textarea (e.g., "Prof. Rossi non puo insegnare il lunedi mattina") and click "Aggiungi vincolo" **Then** the constraint is saved with status "pending" and appears in the list below with a "pending" badge

2. **Given** I have submitted multiple constraints **When** I view the constraints list **Then** I see all constraints with their status badges (pending/verified/rejected) and original text

3. **Given** the Constraint model needs to be persisted **When** I check the database **Then** a `constraints` table exists with columns: id (UUID PK), timetable_id (FK to timetables.id), natural_language_text (String, max 1000), formal_representation (JSON, nullable), status (String, default "pending"), created_at **And** an Alembic migration was created for this table

4. **Given** the textarea accepts Italian text **When** I submit a constraint **Then** the text field supports >=500 characters and I can submit >=10 constraints per timetable

5. **Given** pending constraints exist **When** I view the page **Then** I see a "Verifica vincoli" button linking to the verification flow (non-functional until Epic 3)

6. **Given** I try to access `/orario/{id}/vincoli` for a timetable I do not own **When** the page loads **Then** I receive a 403 Forbidden response

7. **Given** I submit an empty constraint (blank textarea) **When** the form is processed **Then** I see an Italian validation error and remain on the page with existing constraints visible

8. **Given** I am a Professor (not Responsible Professor) **When** I try to access `/orario/{id}/vincoli` **Then** I receive a 403 Forbidden response

## Tasks / Subtasks

- [ ] Task 1: Create Constraint model and Alembic migration (AC: #3)
  - [ ] 1.1 Create `easyorario/models/constraint.py` -- Constraint ORM model with UUID PK, timetable_id (FK -> timetables.id, CASCADE), natural_language_text (String(1000)), formal_representation (JSON, nullable), status (String(20), default "pending"), created_at
  - [ ] 1.2 Add relationship: `Constraint.timetable` -> Timetable, `Timetable.constraints` -> list[Constraint]
  - [ ] 1.3 Export Constraint from `easyorario/models/__init__.py`
  - [ ] 1.4 Generate Alembic migration: `just db-revision "create constraints table"`
  - [ ] 1.5 Verify migration applies cleanly: `just db-migrate`

- [ ] Task 2: Create ConstraintRepository (AC: #1, #2, #3)
  - [ ] 2.1 Create `easyorario/repositories/constraint.py` -- ConstraintRepository extending `SQLAlchemyAsyncRepository[Constraint]`
  - [ ] 2.2 Add `get_by_timetable(timetable_id: uuid.UUID) -> list[Constraint]` method ordered by created_at ascending
  - [ ] 2.3 Export from `easyorario/repositories/__init__.py`

- [ ] Task 3: Create ConstraintService (AC: #1, #2, #4, #7)
  - [ ] 3.1 Create `easyorario/services/constraint.py` -- ConstraintService with `add_constraint()` and `list_constraints()` methods
  - [ ] 3.2 `add_constraint(timetable_id, natural_language_text)`: validate text non-empty after strip, max 1000 chars; create Constraint with status="pending"
  - [ ] 3.3 `list_constraints(timetable_id) -> list[Constraint]`: return all constraints for timetable ordered by created_at
  - [ ] 3.4 Add `delete_constraint(constraint_id, timetable_id)` for future use (optional, only if simple)

- [ ] Task 4: Add domain exceptions and Italian messages (AC: #7)
  - [ ] 4.1 Add `InvalidConstraintDataError` to `easyorario/exceptions.py` with error_key
  - [ ] 4.2 Add Italian constraint validation messages to `easyorario/i18n/errors.py`

- [ ] Task 5: Create ConstraintController (AC: #1, #2, #5, #6, #7, #8)
  - [ ] 5.1 Create `easyorario/controllers/constraint.py` with `path="/orario/{timetable_id:uuid}/vincoli"`
  - [ ] 5.2 `GET /` -- Render constraint input page: textarea form + constraint list + "Verifica vincoli" link (if any pending constraints)
  - [ ] 5.3 `POST /` -- Parse textarea, call ConstraintService.add_constraint(), redirect back to GET (PRG pattern)
  - [ ] 5.4 Ownership guard: verify `request.user.id == timetable.owner_id`, raise 403 otherwise
  - [ ] 5.5 Guard: `requires_responsible_professor` on both GET and POST routes
  - [ ] 5.6 Remove stub vincoli route from TimetableController

- [ ] Task 6: Create constraint input template (AC: #1, #2, #4, #5)
  - [ ] 6.1 Replace `templates/pages/timetable_constraints.html` with full constraint page
  - [ ] 6.2 Layout: timetable identifier header, textarea form with "Aggiungi vincolo" button, constraint list below
  - [ ] 6.3 Each constraint card: original text + status badge (pending=default, verified=green, rejected=red)
  - [ ] 6.4 "Verifica vincoli" button visible when any pending constraints exist (links to `/orario/{id}/vincoli/verifica`, non-functional stub)
  - [ ] 6.5 All labels and text in Italian, CSRF token included
  - [ ] 6.6 Textarea: `maxlength="1000"`, `minlength="1"`, placeholder with Italian example

- [ ] Task 7: Register DI providers and controller in app.py (AC: #1)
  - [ ] 7.1 Add `provide_constraint_repository` and `provide_constraint_service` DI functions
  - [ ] 7.2 Register in `dependencies` dict in `create_app()`
  - [ ] 7.3 Add ConstraintController to `route_handlers` list
  - [ ] 7.4 Also inject TimetableRepository into ConstraintController for ownership check

- [ ] Task 8: Write tests (AC: #1-#8)
  - [ ] 8.1 `tests/models/test_constraint.py`: model creation, defaults (status="pending"), timetable relationship
  - [ ] 8.2 `tests/repositories/test_constraint_repository.py`: add_constraint persists, get_by_timetable returns ordered list, get_by_timetable returns empty for other timetable
  - [ ] 8.3 `tests/services/test_constraint.py`: add_constraint happy path, empty text raises error, text > 1000 chars raises error, list_constraints returns ordered list
  - [ ] 8.4 `tests/controllers/test_constraint.py`: GET renders form with constraint list, POST adds constraint and redirects, POST with empty text shows error, GET as Professor returns 403, GET for non-owned timetable returns 403, "Verifica vincoli" button appears when pending constraints exist, GET with no constraints shows empty state

## Dev Notes

### Architecture Patterns & Constraints

- **Layered architecture applies:** ConstraintController (HTTP) -> ConstraintService (business logic) -> ConstraintRepository (data access) -> SQLite. One-way dependency.
- **Separate controller for constraints:** Architecture specifies `ConstraintController` as a distinct controller. Create at `easyorario/controllers/constraint.py` with path `/orario/{timetable_id:uuid}/vincoli`. Remove the stub vincoli route from TimetableController.
- **Dependency injection:** Inject `ConstraintService` and `TimetableRepository` (for ownership check) into ConstraintController. Follow existing DI pattern in `app.py`.
- **Guards enforce authorization:** Apply `requires_responsible_professor` on both GET and POST routes. Additionally, verify timetable ownership in the controller (check `timetable.owner_id == request.user.id`).
- **PRG pattern for POST:** After adding a constraint, redirect back to the constraints page (`GET /orario/{id}/vincoli`). `autocommit_handler_maker(commit_on_redirect=True)` ensures the constraint is persisted before the redirect.

### Constraint Data Model Design

- **`id`**: UUID primary key, auto-generated
- **`timetable_id`**: UUID FK -> `timetables.id` with `ondelete="CASCADE"`. When a timetable is deleted, all its constraints are deleted too.
- **`natural_language_text`**: String(1000) -- the original Italian text entered by the user
- **`formal_representation`**: JSON, nullable -- will be populated by LLM translation in Epic 3. NULL until translated.
- **`status`**: String(20), default "pending". Valid values: "pending" (just entered), "verified" (approved after LLM translation), "rejected" (rejected after translation). Status transitions happen in Epic 3, NOT in this story.
- **`created_at`**: DateTime with server default `func.now()`

**Relationships:**
- `Constraint.timetable` -> Timetable (many-to-one, `lazy="selectin"`)
- `Timetable.constraints` -> list[Constraint] (one-to-many, `lazy="selectin"`)

**Index:** Add `ix_constraints_timetable_id` on `timetable_id` for efficient filtering.

### Ownership Verification Pattern

The constraints page must verify that the authenticated user owns the timetable. Pattern:

```python
@get("/", guards=[requires_responsible_professor])
async def list_constraints(
    self,
    request: Request,
    timetable_id: uuid.UUID,
    timetable_repo: TimetableRepository,
    constraint_service: ConstraintService,
) -> Template:
    timetable = await timetable_repo.get(timetable_id)
    if timetable.owner_id != request.user.id:
        raise NotAuthorizedException(detail="Insufficient permissions")
    constraints = await constraint_service.list_constraints(timetable_id)
    has_pending = any(c.status == "pending" for c in constraints)
    return Template(
        template_name="pages/timetable_constraints.html",
        context={
            "timetable": timetable,
            "constraints": constraints,
            "has_pending": has_pending,
            "request": request,
        },
    )
```

Use `timetable_repo.get(timetable_id)` -- if not found, Advanced Alchemy raises `NotFoundError` which Litestar will handle as 404 automatically.

### SessionAuth & Route Exclusion

The vincoli routes are NOT in the SessionAuth `exclude` list, so they require authentication by default. The `requires_responsible_professor` guard provides the additional role check.

### Template Design

The constraints page layout:

```
[Timetable header: class_identifier - school_year]

[Textarea form]
  <textarea name="text" maxlength="1000" placeholder="Es: Prof. Rossi non puo...">
  <button type="submit">Aggiungi vincolo</button>

[Constraint list]
  For each constraint:
    <div class="constraint-card">
      <span badge data-variant="default|success|error">pending|verified|rejected</span>
      <p>constraint text</p>
    </div>

  If has_pending:
    <a href="/orario/{id}/vincoli/verifica">Verifica vincoli</a>
    (disabled/non-functional link until Epic 3)

  If no constraints:
    <p>Nessun vincolo inserito.</p>
```

Use Oat UI components:
- `<div role="alert">` for validation errors
- Badge styling for status indicators
- Standard form elements with CSRF

### Project Structure Notes

- **Flat layout confirmed:** `easyorario/` at project root (no `src/`). The architecture doc mentions `src/easyorario/` but the actual project uses `easyorario/` directly. Follow what exists.
- **Tests at `tests/`** at project root, mirroring `easyorario/` structure.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.2]
- [Source: _bmad-output/planning-artifacts/architecture.md#Data Architecture]
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns & Consistency Rules]
- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure & Boundaries]
- [Source: _bmad-output/planning-artifacts/architecture.md#Architectural Boundaries]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Key Interaction Patterns]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Constraint Input]
- [Source: _bmad-output/implementation-artifacts/2-1-create-new-timetable.md]
- [Source: CLAUDE.md#Architecture]

### Architecture Compliance

**Boundary Rules -- MUST follow:**

| Rule | This Story's Application |
|---|---|
| Controller -> Service -> Repository (one-way) | ConstraintController calls ConstraintService; ConstraintService calls ConstraintRepository. Controller NEVER touches ConstraintRepository directly (except TimetableRepository for ownership check). |
| Controllers handle HTTP only -- no business logic | Controller parses form data, passes raw text to service. Service validates and creates model. |
| Guards enforce authorization declaratively | `requires_responsible_professor` guard on GET and POST. Ownership check in controller (timetable owner_id match). |
| Italian user-facing text, English code/logs | Template text in Italian. Python identifiers, comments, log messages in English. |
| `structlog` for all logging, never `print()` | Log constraint creation: `_log.ainfo("constraint_added", constraint_id=..., timetable_id=...)` |
| Use Litestar DI, never manual instantiation | ConstraintRepository and ConstraintService provided via Litestar's DI. |
| `snake_case` for Python/JSON, `kebab-case` for URLs | Table: `constraints`. Columns: `timetable_id`, `natural_language_text`. URL: `/orario/{id}/vincoli`. |
| `jj` for VCS, never raw `git` | All commits via `jj commit -m "message"`. |

**Anti-Patterns -- NEVER do:**

- Do NOT hardcode Italian strings in Python code -- use templates or `i18n/errors.py`
- Do NOT implement LLM translation, constraint verification, or status transitions in this story (that's Epic 3)
- Do NOT create Revision or Comment models
- Do NOT add complex JavaScript -- the form is a standard HTML form POST with PRG
- Do NOT use bare `except:` or catch `Exception` without re-raising
- Do NOT use `git` commands -- use `jj` exclusively
- Do NOT add `from __future__ import annotations`
- Do NOT create a constraint controller inside `timetable.py` -- use a separate `constraint.py`

### Library & Framework Requirements

**Litestar -- Key APIs for this story:**

| API | Usage | Import |
|---|---|---|
| `Request.user` | Access authenticated User instance | `from litestar import Request` |
| `Template` | Render Jinja2 template response | `from litestar.response import Template` |
| `Redirect` | HTTP redirect after POST | `from litestar.response import Redirect` |
| `Controller` | Base class for route controllers | `from litestar import Controller` |
| `get`, `post` | Route decorators | `from litestar import get, post` |
| `Body` | Parse form-encoded POST data | `from litestar.params import Body` |
| `RequestEncodingType` | Specify URL-encoded form | `from litestar.enums import RequestEncodingType` |
| `NotAuthorizedException` | Raise 403 for ownership failures | `from litestar.exceptions import NotAuthorizedException` |

**SQLAlchemy -- Constraint model:**

```python
from sqlalchemy import ForeignKey, String, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

class Constraint(Base):
    __tablename__ = "constraints"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    timetable_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("timetables.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    natural_language_text: Mapped[str] = mapped_column(String(1000), nullable=False)
    formal_representation: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    timetable: Mapped["Timetable"] = relationship(back_populates="constraints", lazy="selectin")
```

**No new dependencies required.** Everything needed is already in `pyproject.toml`.

### File Structure Requirements

**Files to CREATE:**

```
easyorario/models/constraint.py                   (CREATE: Constraint ORM model)
easyorario/repositories/constraint.py              (CREATE: ConstraintRepository)
easyorario/services/constraint.py                  (CREATE: ConstraintService)
easyorario/controllers/constraint.py               (CREATE: ConstraintController)
tests/models/test_constraint.py                     (CREATE: model tests)
tests/repositories/test_constraint_repository.py    (CREATE: repository tests)
tests/services/test_constraint.py                   (CREATE: service tests)
tests/controllers/test_constraint.py                (CREATE: controller integration tests)
alembic/versions/*_create_constraints_table.py      (CREATE: auto-generated migration)
```

**Files to UPDATE:**

```
easyorario/models/__init__.py                      (UPDATE: export Constraint)
easyorario/models/timetable.py                     (UPDATE: add constraints relationship)
easyorario/repositories/__init__.py                (UPDATE: export ConstraintRepository)
easyorario/controllers/timetable.py                (UPDATE: remove vincoli stub route)
easyorario/app.py                                  (UPDATE: add DI providers, register ConstraintController)
easyorario/exceptions.py                           (UPDATE: add InvalidConstraintDataError)
easyorario/i18n/errors.py                          (UPDATE: add constraint validation messages)
templates/pages/timetable_constraints.html         (UPDATE: replace stub with full constraint page)
```

**Files NOT to touch:**

```
easyorario/models/user.py                          (NO CHANGE)
easyorario/services/auth.py                        (NO CHANGE)
easyorario/services/timetable.py                   (NO CHANGE)
easyorario/controllers/auth.py                     (NO CHANGE)
easyorario/controllers/dashboard.py                (NO CHANGE)
easyorario/guards/auth.py                          (NO CHANGE)
templates/base.html                                (NO CHANGE)
templates/pages/dashboard.html                     (NO CHANGE)
templates/pages/timetable_new.html                 (NO CHANGE)
```

### Testing Requirements

**TDD Workflow -- Mandatory:**

1. **Red:** Write a small, focused test that fails
2. **Green:** Write minimum code to make it pass
3. **Refactor/Tidy:** Clean up only if needed, all tests stay green
4. **Repeat**

Test naming: `test_{action}_{condition}_{expected_result}`

**Test Fixtures Needed:**

Reuse existing fixtures from `tests/conftest.py`:
- `client` -- AsyncTestClient with in-memory DB
- `db_session` -- standalone async session for model/repo tests
- `authenticated_client` -- logged-in Responsible Professor
- `authenticated_professor_client` -- logged-in Professor
- `_get_csrf_token()` helper

New fixtures needed:
```python
@pytest.fixture
async def timetable(authenticated_client, db_session) -> Timetable:
    """A draft timetable owned by the authenticated RP user."""
    # Create via POST to /orario/nuovo or directly via DB

@pytest.fixture
async def constraint_data() -> dict[str, str]:
    """Valid form data for adding a constraint."""
    return {"text": "Prof. Rossi non puo insegnare il lunedi mattina"}
```

**Required Test Cases:**

| Test File | Test Name | Verifies |
|---|---|---|
| `test_constraint.py` (model) | `test_create_constraint_has_correct_defaults` | status="pending", created_at set, formal_representation=None |
| `test_constraint.py` (model) | `test_constraint_timetable_relationship` | FK relationship works |
| `test_constraint_repository.py` | `test_add_constraint_persists` | Basic persistence |
| `test_constraint_repository.py` | `test_get_by_timetable_returns_ordered_list` | Ordered by created_at |
| `test_constraint_repository.py` | `test_get_by_timetable_returns_empty_for_other` | Isolation between timetables |
| `test_constraint.py` (service) | `test_add_constraint_with_valid_text_creates_pending` | Happy path |
| `test_constraint.py` (service) | `test_add_constraint_with_empty_text_raises` | Validation: non-empty |
| `test_constraint.py` (service) | `test_add_constraint_with_text_over_1000_chars_raises` | Validation: max length |
| `test_constraint.py` (service) | `test_list_constraints_returns_ordered` | Ordering |
| `test_constraint.py` (controller) | `test_get_vincoli_renders_form_with_timetable_info` | Page renders with timetable context |
| `test_constraint.py` (controller) | `test_post_vincoli_adds_constraint_and_redirects` | PRG: add + redirect |
| `test_constraint.py` (controller) | `test_post_vincoli_with_empty_text_shows_error` | Validation error |
| `test_constraint.py` (controller) | `test_get_vincoli_as_professor_returns_403` | Role guard |
| `test_constraint.py` (controller) | `test_get_vincoli_for_non_owned_timetable_returns_403` | Ownership check |
| `test_constraint.py` (controller) | `test_get_vincoli_shows_verifica_button_when_pending` | "Verifica vincoli" button |
| `test_constraint.py` (controller) | `test_get_vincoli_with_no_constraints_shows_empty_state` | Empty state message |
| `test_constraint.py` (controller) | `test_get_vincoli_for_nonexistent_timetable_returns_404` | Not found handling |

### Previous Story Intelligence

**From Story 2.1 (Create New Timetable) -- Direct predecessor:**

- **TimetableController has a vincoli stub** at `GET /orario/{timetable_id:uuid}/vincoli` returning a placeholder template. This must be removed and replaced by the new ConstraintController.
- **`templates/pages/timetable_constraints.html`** exists as a stub. Replace with the full constraint input page.
- **`autocommit_handler_maker(commit_on_redirect=True)`** is configured -- the redirect after POST will auto-commit the session.
- **Timetable model** already has UUID PK, owner_id FK. Add `constraints` relationship to it.
- **DI pattern**: follow the existing `provide_timetable_repository` / `provide_timetable_service` pattern.
- **Test pattern**: follow the existing controller test pattern with `_get_csrf_token()`, `follow_redirects=False`, CSRF header in POST requests.
- **Exception pattern**: `InvalidTimetableDataError(error_key)` -> mapped via `i18n/errors.py`. Follow same for `InvalidConstraintDataError(error_key)`.

**Key learnings from 2.1:**
- `request.user` raises `KeyError` not `AttributeError` when user not in scope -- use `request.scope.get("user")` in exception handlers
- Service accepts raw strings, does all parsing/validation, raises domain exceptions with error_key
- Controller catches domain exceptions, re-renders template with error message

### Git Intelligence

**Recent commit pattern from Story 2.1:**
```
5cf39fc story 2.1: code review fixes -- missing tests, error key, file list
9a4fb4b story 2.1: finalize -- update story and sprint status to review
e17101a story 2.1: controller, templates, DI wiring, session-cached user auth (tasks 5-7)
caf6b44 story 2.1: timetable service with validation, domain exceptions, i18n messages (tasks 3-4)
c1ad674 story 2.1: timetable repository with get_by_owner (task 2)
a43640e story 2.1: timetable model, user relationship, and alembic migration (task 1)
```

Follow same atomic commit pattern: one commit per task group, descriptive message format `story 2.2: description (task N)`.

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
