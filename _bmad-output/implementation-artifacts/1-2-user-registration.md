# Story 1.2: User Registration

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a Responsible Professor,
I want to register with my email and password,
so that I can create an account to manage timetables.

## Acceptance Criteria

1. **Given** I am on the registration page at `/registrati` **When** I submit a valid email and password (>=8 characters) **Then** a User is created with Argon2-hashed password and a role **And** I am redirected to the login page with a success message in Italian

2. **Given** I submit a registration with an already-used email **When** the form is processed **Then** I see an Italian error message indicating the email is taken

3. **Given** I submit a password shorter than 8 characters **When** the form is processed **Then** I see an Italian validation error

4. **Given** the User model needs to be persisted **When** I check the database **Then** a `users` table exists with columns: id, email, hashed_password, role, created_at **And** an Alembic migration was created for this table

## Tasks / Subtasks

- [ ] Task 1: Create User model (AC: #4)
  - [ ] 1.1 Create `src/easyorario/models/user.py` — User SQLAlchemy model
  - [ ] 1.2 Columns: `id` (UUID, PK), `email` (String, unique, not null), `hashed_password` (String, not null), `role` (String, not null, default "responsible_professor"), `created_at` (DateTime, server default)
  - [ ] 1.3 Export User from `src/easyorario/models/__init__.py`
  - [ ] 1.4 Create Alembic migration: `create_users_table`
  - [ ] 1.5 Verify migration runs successfully with `just db-migrate`

- [ ] Task 2: Create UserRepository (AC: #1, #2)
  - [ ] 2.1 Create `src/easyorario/repositories/user.py` — Advanced Alchemy SQLAlchemy repository
  - [ ] 2.2 Implement `get_by_email(email)` method for duplicate checking
  - [ ] 2.3 Export from `src/easyorario/repositories/__init__.py`

- [ ] Task 3: Create AuthService (AC: #1, #2, #3)
  - [ ] 3.1 Add `argon2-cffi` to `pyproject.toml` dependencies
  - [ ] 3.2 Create `src/easyorario/services/auth.py`
  - [ ] 3.3 Implement `hash_password(password: str) -> str` using Argon2
  - [ ] 3.4 Implement `register_user(email, password, role) -> User` with validation:
    - Validate email format (basic check: contains @ and a dot in domain portion). Raise `InvalidEmailError` if invalid.
    - Validate password length >= 8 characters
    - Check email uniqueness via UserRepository
    - Hash password with Argon2
    - Create User via repository
    - Return created User
  - [ ] 3.5 Raise domain-specific exceptions for validation failures (use Italian error keys from i18n)
  - [ ] 3.6 Note: password confirmation matching is validated in the **controller** (UI concern), not the service

- [ ] Task 4: Create Italian error messages for auth (AC: #1, #2, #3)
  - [ ] 4.1 Create or update `src/easyorario/i18n/errors.py` with auth error mappings:
    - `email_taken`: "Questo indirizzo email e' gia' registrato"
    - `password_too_short`: "La password deve contenere almeno 8 caratteri"
    - `password_mismatch`: "Le password non corrispondono"
    - `registration_success`: "Registrazione completata. Effettua l'accesso."
    - `invalid_email`: "Indirizzo email non valido"

- [ ] Task 5: Create registration template (AC: #1, #2, #3)
  - [ ] 5.1 Create `templates/pages/register.html` extending `base.html`
  - [ ] 5.2 Form with: email input, password input, confirm password input, submit button ("Registrati")
  - [ ] 5.3 Use Oat UI semantic form elements: `<label data-field>` wrapping, native `<input>` types
  - [ ] 5.4 Display error messages using Oat `role="alert"` with `data-variant="error"`
  - [ ] 5.5 Include CSRF token via `{{ csrf_input | safe }}` (renders the hidden input automatically)
  - [ ] 5.6 Link to login page: "Hai gia' un account? Accedi"

- [ ] Task 6: Create AuthController — registration endpoint (AC: #1, #2, #3)
  - [ ] 6.1 Create `src/easyorario/controllers/auth.py` with `AuthController` class
  - [ ] 6.2 `GET /registrati` — renders registration form template
  - [ ] 6.3 `POST /registrati` — processes registration:
    - Extract email, password, password_confirm from form data
    - Validate password_confirm matches password (if not, re-render with Italian error "Le password non corrispondono")
    - Call AuthService.register_user()
    - On success: redirect to `/accedi?msg=registration_success` (query param for cross-redirect message)
    - On validation error: re-render form with Italian error message
    - On duplicate email: re-render form with Italian error message
  - [ ] 6.4 Register AuthController in app.py route handlers
  - [ ] 6.5 Create `templates/partials/flash_messages.html` partial for reusable flash message display

- [ ] Task 7: Configure CSRF middleware (AC: #1)
  - [ ] 7.1 Enable Litestar CSRF middleware in app.py configuration
  - [ ] 7.2 Ensure CSRF token is available in templates and included in all form POSTs
  - [ ] 7.3 Configure CSRF secret from environment/config

- [ ] Task 8: Write tests (AC: #1, #2, #3, #4)
  - [ ] 8.1 `tests/models/test_user.py` — Test User model creation, column constraints, unique email index
  - [ ] 8.2 `tests/repositories/test_user_repository.py` — Test get_by_email, create user
  - [ ] 8.3 `tests/services/test_auth.py`:
    - `test_hash_password_returns_argon2_hash`
    - `test_register_user_with_valid_input_creates_user`
    - `test_register_user_with_duplicate_email_raises_error`
    - `test_register_user_with_short_password_raises_error`
    - `test_register_user_with_invalid_email_raises_error`
  - [ ] 8.4 `tests/controllers/test_auth.py`:
    - `test_get_registrati_returns_200_with_form`
    - `test_post_registrati_with_valid_data_redirects_to_accedi`
    - `test_post_registrati_with_duplicate_email_shows_error`
    - `test_post_registrati_with_short_password_shows_error`
    - `test_post_registrati_with_mismatched_passwords_shows_error`
    - `test_post_registrati_without_csrf_token_returns_403`
    - Note: redirect test checks for HTTP 302/303 with `Location: /accedi?msg=registration_success`. Do NOT follow the redirect.

## Dev Notes

### Architecture Patterns & Constraints

- **Layered architecture applies:** AuthController (HTTP) → AuthService (business logic) → UserRepository (data access). Controller never hashes passwords or queries DB directly.
- **Dependency injection:** Use Litestar's DI to inject AuthService into AuthController, and UserRepository into AuthService. Never manually instantiate.
- **Repository pattern:** Use Advanced Alchemy's `SQLAlchemyAsyncRepository` as the base class for UserRepository. Import: `from advanced_alchemy.repository import SQLAlchemyAsyncRepository`. This gives you CRUD operations for free.
- **Italian-only user-facing text:** All form labels, error messages, success messages in Italian. Code and logs in English.
- **No login/session in this story:** Registration only. User is redirected to `/accedi` after registration. The full login page is built in story 1.3. For this story, create a minimal placeholder at `GET /accedi` that returns a simple template with "Pagina di accesso in costruzione" (Login page under construction). This ensures the redirect target exists and integration tests can verify the full flow. Story 1.3 will replace this placeholder.

### Previous Story (1.1) Established

The following already exist from story 1.1 — **do NOT recreate**:
- `src/easyorario/app.py` — Litestar app factory (UPDATE: add AuthController to route_handlers, add CSRF middleware)
- `src/easyorario/config.py` — Settings (UPDATE: add CSRF_SECRET)
- `src/easyorario/exceptions.py` — EasyorarioError base (UPDATE: add auth-specific exceptions)
- `src/easyorario/models/base.py` — SQLAlchemy base (REUSE as parent for User model)
- `templates/base.html` — Base layout with Oat UI (REUSE: register.html extends this)
- `tests/conftest.py` — Test fixtures (REUSE/UPDATE: may need user factory fixture)
- Alembic configured — just create a new migration
- structlog configured — just use it
- justfile — already has `just db-migrate`, `just test`, etc.

### User Model Specification

```python
# src/easyorario/models/user.py
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base  # from story 1.1

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="responsible_professor")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

**Role values:** `"responsible_professor"` or `"professor"`. For this story, all registrations default to `"responsible_professor"`. Role selection UI is not required (can be added later or managed manually).

**Database naming:** Table = `users` (plural, snake_case). Columns = snake_case. Index on email: `ix_users_email`.

### Argon2 Password Hashing

```python
# src/easyorario/services/auth.py
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

ph = PasswordHasher()

def hash_password(password: str) -> str:
    return ph.hash(password)

def verify_password(hashed_password: str, password: str) -> bool:
    """Verify a password against its Argon2 hash. Arg order matches argon2-cffi's ph.verify(hash, password)."""
    try:
        return ph.verify(hashed_password, password)
    except VerifyMismatchError:
        return False
```

**Note:** Include `verify_password` now even though login is story 1.3 — it belongs in the same service and is trivial to add with the hash function.

### Registration Template (Oat UI)

```html
<!-- templates/pages/register.html -->
{% extends "base.html" %}
{% block content %}
<div class="container">
  <div class="row">
    <div class="col-6 offset-3">
      <h1>Registrati</h1>

      {% if error %}
      <div role="alert" data-variant="error">{{ error }}</div>
      {% endif %}

      <form method="post" action="/registrati">
        {{ csrf_input | safe }}

        <label data-field>
          Email
          <input type="email" name="email" required placeholder="nome@esempio.it"
                 value="{{ email_value | default('') }}">
        </label>

        <label data-field>
          Password
          <input type="password" name="password" required minlength="8"
                 placeholder="Minimo 8 caratteri">
        </label>

        <label data-field>
          Conferma password
          <input type="password" name="password_confirm" required minlength="8"
                 placeholder="Ripeti la password">
        </label>

        <button type="submit">Registrati</button>
      </form>

      <p>Hai gia' un account? <a href="/accedi">Accedi</a></p>
    </div>
  </div>
</div>
{% endblock %}
```

### Error Display Partial

```html
<!-- templates/partials/flash_messages.html -->
{% if error %}
<div role="alert" data-variant="error">{{ error }}</div>
{% endif %}
{% if success %}
<div role="alert" data-variant="success">{{ success }}</div>
{% endif %}
```

**Flash message strategy for PoC:** Use URL query parameters for cross-redirect success messages (e.g., `/accedi?msg=registration_success`) and template context variables for inline errors on the same page. This avoids the complexity of session-based flash plugins. The receiving controller reads the `msg` query param, looks up the Italian message from `i18n/errors.py`, and passes it as `success` context variable.

### CSRF Configuration

Litestar's built-in CSRF middleware:
```python
from litestar.config.csrf import CSRFConfig

csrf_config = CSRFConfig(
    secret=settings.CSRF_SECRET,  # from config.py / env
    cookie_name="csrftoken",
    header_name="x-csrftoken",
)

app = Litestar(
    csrf_config=csrf_config,
    ...
)
```

In templates, include the CSRF token with `{{ csrf_input | safe }}`. This is automatically available when `CSRFConfig` is configured. Do NOT manually construct a hidden input.

### Litestar Controller Pattern

```python
from litestar import Controller, get, post, Request
from litestar.response import Template, Redirect
from litestar.enums import RequestEncodingType
from litestar.params import Body
from typing import Annotated
from dataclasses import dataclass

@dataclass
class RegisterFormData:
    email: str
    password: str
    password_confirm: str

class AuthController(Controller):
    path = ""  # routes defined per method

    @get("/registrati")
    async def show_register(self) -> Template:
        return Template(template_name="pages/register.html")

    @post("/registrati")
    async def register(
        self,
        request: Request,
        data: Annotated[RegisterFormData, Body(media_type=RequestEncodingType.URL_ENCODED)],
        auth_service: AuthService,
    ) -> Template | Redirect:
        # 1. Validate password confirmation (UI concern, controller handles it)
        if data.password != data.password_confirm:
            return Template("pages/register.html", context={"error": ERRORS["password_mismatch"], "email_value": data.email})
        # 2. Call service (handles email validation, uniqueness, hashing)
        try:
            await auth_service.register_user(data.email, data.password)
            return Redirect(path="/accedi?msg=registration_success")
        except (EmailAlreadyTakenError, PasswordTooShortError, InvalidEmailError) as e:
            return Template("pages/register.html", context={"error": ERRORS[e.error_key], "email_value": data.email})
```

**Form data parsing:** Use `Body(media_type=RequestEncodingType.URL_ENCODED)` with a dataclass for typed form extraction. Do NOT use `sync_to_thread=False` on `async def` handlers (it's a no-op and generates warnings).

### Error Handling for Registration

Define auth exceptions in `exceptions.py`:
```python
class EmailAlreadyTakenError(EasyorarioError):
    """Raised when registration email is already in use."""

class PasswordTooShortError(EasyorarioError):
    """Raised when password doesn't meet minimum length."""

class InvalidEmailError(EasyorarioError):
    """Raised when email format is invalid."""

class PasswordMismatchError(EasyorarioError):
    """Raised when password and confirmation don't match."""
```

Controller catches these and re-renders the form with the appropriate Italian error message from `i18n/errors.py`.

### UserRepository Pattern

```python
# src/easyorario/repositories/user.py
from advanced_alchemy.repository import SQLAlchemyAsyncRepository
from easyorario.models.user import User

class UserRepository(SQLAlchemyAsyncRepository[User]):
    model_type = User
```

### Dependency Injection Wiring

```python
# In app.py or a dedicated deps module
from litestar.di import Provide
from sqlalchemy.ext.asyncio import AsyncSession

async def provide_user_repository(db_session: AsyncSession) -> UserRepository:
    return UserRepository(session=db_session)

async def provide_auth_service(user_repo: UserRepository) -> AuthService:
    return AuthService(user_repo=user_repo)

# Register in Litestar app constructor:
app = Litestar(
    route_handlers=[AuthController],
    dependencies={
        "user_repo": Provide(provide_user_repository),
        "auth_service": Provide(provide_auth_service),
    },
    ...
)
```

The `db_session: AsyncSession` is automatically provided by Advanced Alchemy's plugin. Litestar's DI resolves the chain: `AsyncSession` -> `UserRepository` -> `AuthService` -> controller method parameter.

### Version Control

- **Prefer `jj` (Jujutsu)** for VCS operations
- **If `jj` is not available**, use `git` with equivalent commands
- Commit after each meaningful TDD green-refactor cycle

### TDD Workflow (Mandatory)

1. **Red:** Write failing test first
2. **Green:** Minimum code to pass
3. **Refactor:** Clean up only if needed
4. **Repeat**

Test naming: `test_{action}_{condition}_{expected_result}`

### Project Structure Notes

Files to CREATE in this story:
```
src/easyorario/models/user.py           (CREATE)
src/easyorario/repositories/user.py     (CREATE)
src/easyorario/services/auth.py         (CREATE)
src/easyorario/controllers/auth.py      (CREATE)
src/easyorario/i18n/errors.py           (CREATE)
templates/pages/register.html           (CREATE)
templates/partials/flash_messages.html  (CREATE)
alembic/versions/*_create_users_table.py (CREATE — via alembic autogenerate)
tests/models/test_user.py              (CREATE)
tests/repositories/test_user_repository.py (CREATE)
tests/services/test_auth.py            (CREATE)
tests/controllers/test_auth.py         (CREATE)
```

Files to UPDATE:
```
pyproject.toml                          (UPDATE: add argon2-cffi)
src/easyorario/app.py                   (UPDATE: add AuthController, CSRF config)
src/easyorario/config.py                (UPDATE: add CSRF_SECRET)
src/easyorario/exceptions.py            (UPDATE: add EmailAlreadyTakenError, PasswordTooShortError, InvalidEmailError, PasswordMismatchError)
src/easyorario/models/__init__.py       (UPDATE: export User)
src/easyorario/repositories/__init__.py (UPDATE: export UserRepository)
tests/conftest.py                       (UPDATE: add user factory fixture if needed)
```

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.2]
- [Source: _bmad-output/planning-artifacts/architecture.md#Authentication & Security]
- [Source: _bmad-output/planning-artifacts/architecture.md#Data Architecture]
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns & Consistency Rules]
- [Source: _bmad-output/planning-artifacts/architecture.md#Architectural Boundaries]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Page Map & User Journeys]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Design System]
- [Source: _bmad-output/implementation-artifacts/1-1-project-skeleton-development-infrastructure.md — Previous story context]
- [Source: docs/PRD.md#FR-11]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
