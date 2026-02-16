# Story 1.3: User Login & Session Management

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a registered user,
I want to log in with my email and password,
so that I can access the system securely.

## Acceptance Criteria

1. **Given** I am on the login page at `/accedi` **When** I submit valid credentials **Then** a session is created (server-side, cookie-identified) and I am redirected to `/dashboard`

2. **Given** I submit invalid credentials **When** the form is processed **Then** I see an Italian error message and remain on the login page

3. **Given** I am logged in **When** I click logout **Then** my session is destroyed and I am redirected to `/accedi`

4. **Given** CSRF protection is enabled **When** a form POST is submitted without a valid CSRF token **Then** the request is rejected

5. **Given** I am not authenticated **When** I try to access a protected page **Then** I am redirected to `/accedi`

## Tasks / Subtasks

- [ ] Task 1: Configure SessionAuth middleware in app.py (AC: #1, #5)
  - [ ] 1.1 Create `retrieve_user_handler` function in `src/easyorario/app.py` — loads User from DB using `user_id` stored in session dict
  - [ ] 1.2 Configure `ServerSideSessionConfig` with sensible defaults (cookie name `session`, httponly=True, samesite=lax)
  - [ ] 1.3 Create `SessionAuth[User, ServerSideSessionBackend]` instance with `retrieve_user_handler` and `exclude` paths
  - [ ] 1.4 Set `exclude` to: `["/", "/accedi", "/registrati", "/health", "/static/", "/schema"]` (include `/` so home page is accessible without auth)
  - [ ] 1.5 Wire `session_auth.on_app_init` into Litestar app via `on_app_init` parameter
  - [ ] 1.6 Register a `MemoryStore` (or `FileStore` for persistence) under key `"sessions"` in app's `stores` config
  - [ ] 1.7 Verify CSRF config from story 1.2 still works alongside SessionAuth

- [ ] Task 2: Update AuthService with login logic (AC: #1, #2)
  - [ ] 2.1 Update `src/easyorario/services/auth.py`
  - [ ] 2.2 Implement `authenticate_user(email: str, password: str) -> User` method:
    - Look up user by email via UserRepository.get_by_email()
    - Verify password with `verify_password()` (already exists from story 1.2)
    - Raise `InvalidCredentialsError` if user not found or password mismatch
    - Return User on success
  - [ ] 2.3 Use constant-time comparison — Argon2's verify already handles this

- [ ] Task 3: Add auth exceptions and Italian messages (AC: #2)
  - [ ] 3.1 Update `src/easyorario/exceptions.py` — add `InvalidCredentialsError(EasyorarioError)`
  - [ ] 3.2 Update `src/easyorario/i18n/errors.py` with login-related messages:
    - `invalid_credentials`: "Email o password non validi"
    - `login_required`: "Effettua l'accesso per continuare"
    - `logout_success`: "Disconnessione effettuata"

- [ ] Task 4: Create login template (AC: #1, #2)
  - [ ] 4.1 Create `templates/pages/login.html` extending `base.html`
  - [ ] 4.2 Form with: email input, password input, submit button ("Accedi")
  - [ ] 4.3 Use Oat UI semantic form elements: `<label data-field>` wrapping, native `<input>` types
  - [ ] 4.4 Display flash messages using `{% include "partials/flash_messages.html" %}` (created in story 1.2)
  - [ ] 4.5 Include CSRF token via `{{ csrf_input | safe }}`
  - [ ] 4.6 Link to registration: "Non hai un account? <a href='/registrati'>Registrati</a>"

- [ ] Task 5: Update AuthController with login/logout endpoints (AC: #1, #2, #3)
  - [ ] 5.1 Update `src/easyorario/controllers/auth.py`
  - [ ] 5.2 `GET /accedi` — renders login form template (exclude from auth via `opt={"exclude_from_auth": True}`)
  - [ ] 5.3 `POST /accedi` — processes login:
    - Extract email, password from form data
    - Call `AuthService.authenticate_user(email, password)`
    - On success: `request.set_session({"user_id": str(user.id)})`, redirect to `/dashboard` with Italian success flash
    - On `InvalidCredentialsError`: re-render form with Italian error message
  - [ ] 5.4 `POST /esci` — processes logout:
    - `request.clear_session()`
    - Redirect to `/accedi?msg=logout_success`
    - Note: `POST /esci` requires a CSRF token (CSRF middleware from story 1.2 is active on all POSTs). The nav bar logout form (story 1.4) must include `{{ csrf_input | safe }}`.
  - [ ] 5.5 Auth exclusions are handled by `SessionAuth.exclude` list (Task 1.4). Routes `/accedi` and `/registrati` are already in the exclude list — no need for `opt={"exclude_from_auth": True}` on individual handlers.

- [ ] Task 6: Create auth guard for route protection (AC: #5)
  - [ ] 6.1 Create `src/easyorario/guards/auth.py`
  - [ ] 6.2 Implement `requires_login(connection, route_handler)` guard:
    - If `connection.user` is None, raise `NotAuthorizedException` (or redirect to `/accedi`)
  - [ ] 6.3 Implement `requires_role(connection, route_handler)` guard:
    - Read `required_role` from `route_handler.opt`
    - If user's role doesn't match, raise `NotAuthorizedException` with 403
  - [ ] 6.4 Export guards from `src/easyorario/guards/__init__.py`
  - [ ] 6.5 Note: Guards are defined here but applied to specific routes in story 1.4 (dashboard). For this story, `SessionAuth.exclude` handles public vs protected route distinction.

- [ ] Task 7: Create placeholder dashboard route (AC: #1)
  - [ ] 7.1 Create `templates/pages/dashboard.html` — minimal placeholder extending `base.html`, displays "Dashboard" heading and user email
  - [ ] 7.2 Create `src/easyorario/controllers/dashboard.py` with `GET /dashboard` that renders the placeholder template
  - [ ] 7.3 Register DashboardController in app.py route_handlers
  - [ ] 7.4 Note: Full dashboard is story 1.4 — this is just so login redirect has a target

- [ ] Task 8: Write tests (AC: #1, #2, #3, #4, #5)
  - [ ] 8.1 `tests/services/test_auth.py` (append to existing from 1.2):
    - `test_authenticate_user_with_valid_credentials_returns_user`
    - `test_authenticate_user_with_invalid_email_raises_error`
    - `test_authenticate_user_with_wrong_password_raises_error`
  - [ ] 8.2 `tests/controllers/test_auth.py` (append to existing from 1.2):
    - `test_get_accedi_returns_200_with_form`
    - `test_post_accedi_with_valid_credentials_redirects_to_dashboard`
    - `test_post_accedi_with_valid_credentials_sets_session`
    - `test_post_accedi_with_invalid_credentials_shows_italian_error`
    - `test_post_esci_clears_session_and_redirects_to_accedi` (must include CSRF token in POST data)
    - `test_post_esci_without_csrf_token_returns_403`
    - `test_post_accedi_without_csrf_token_returns_403`
  - [ ] 8.3 `tests/guards/test_auth_guard.py`:
    - `test_unauthenticated_request_to_protected_route_returns_401_or_redirect`
    - `test_authenticated_request_to_protected_route_succeeds`
  - [ ] 8.4 Update `tests/conftest.py`:
    - Add `authenticated_client` fixture that creates a user and sets up a session
    - Add `user_factory` fixture if not already present from story 1.2

## Dev Notes

### Architecture Patterns & Constraints

- **Layered architecture applies:** AuthController (HTTP) -> AuthService (business logic) -> UserRepository (data access). Controller never verifies passwords or queries DB directly.
- **Dependency injection:** Use Litestar's DI to inject AuthService into AuthController. Never manually instantiate.
- **SessionAuth is the auth backbone:** `SessionAuth.on_app_init` wires up authentication middleware, session middleware, and exclusion logic automatically. Do NOT manually add session middleware to the middleware list — `SessionAuth` handles it internally.
- **Italian-only user-facing text:** All form labels, error messages, success messages in Italian. Code and logs in English.
- **No dashboard logic in this story:** Dashboard is story 1.4. Only create a minimal placeholder so `/dashboard` doesn't 404 after login redirect.

### Previous Story (1.2) Established

The following already exist from story 1.2 — **do NOT recreate**:
- `src/easyorario/models/user.py` — User model with email, hashed_password, role, created_at
- `src/easyorario/repositories/user.py` — UserRepository with `get_by_email(email)` method
- `src/easyorario/services/auth.py` — AuthService with `hash_password()`, `verify_password()`, `register_user()`
- `src/easyorario/controllers/auth.py` — AuthController with `GET/POST /registrati`
- `src/easyorario/i18n/errors.py` — Italian error messages for registration
- `src/easyorario/exceptions.py` — EasyorarioError base, EmailAlreadyTakenError, PasswordTooShortError
- `templates/pages/register.html` — Registration form template
- `templates/partials/flash_messages.html` — Reusable flash message partial
- CSRF middleware configured in `app.py` via `CSRFConfig`

### Previous Story (1.1) Established

- `src/easyorario/app.py` — Litestar app factory (UPDATE: add SessionAuth)
- `src/easyorario/config.py` — Settings (may need SESSION_SECRET or similar)
- `src/easyorario/models/base.py` — SQLAlchemy base
- `templates/base.html` — Base layout with Oat UI
- `tests/conftest.py` — Test fixtures (UPDATE: add authenticated fixtures)
- Alembic configured, structlog configured, justfile with `just test`, etc.

### Litestar SessionAuth Configuration

```python
# src/easyorario/app.py — additions for session auth
import uuid
from typing import Any

from litestar.security.session_auth import SessionAuth
from litestar.middleware.session.server_side import (
    ServerSideSessionBackend,
    ServerSideSessionConfig,
)
from litestar.connection import ASGIConnection
from litestar.stores.memory import MemoryStore

from easyorario.models.user import User


async def retrieve_user_handler(
    session: dict[str, Any],
    connection: ASGIConnection[Any, Any, Any, Any],
) -> User | None:
    """Load user from database using user_id stored in session.

    NOTE: This handler does NOT participate in Litestar's DI system.
    Access the DB session via connection.app to get a managed session
    from the Advanced Alchemy plugin, rather than creating a manual session.
    """
    user_id = session.get("user_id")
    if not user_id:
        return None
    async with alchemy_config.get_session() as db_session:
        return await db_session.get(User, uuid.UUID(user_id))


session_auth = SessionAuth[User, ServerSideSessionBackend](
    retrieve_user_handler=retrieve_user_handler,
    session_backend_config=ServerSideSessionConfig(),
    exclude=["/", "/accedi", "/registrati", "/health", "/static/", "/schema"],
)

app = Litestar(
    route_handlers=[...],
    on_app_init=[session_auth.on_app_init],
    csrf_config=csrf_config,  # from story 1.2
    stores={"sessions": MemoryStore()},
    ...
)
```

**Key points:**

**WARNING: SessionAuth middleware auto-registration.** `SessionAuth.on_app_init` automatically registers the session middleware. Do NOT add `ServerSideSessionConfig` to the Litestar `middleware=[]` parameter. Do NOT add `SessionAuthMiddleware` manually. Doing so will cause duplicate middleware and session corruption. The ONLY session-related configuration needed is:
1. `on_app_init=[session_auth.on_app_init]` — registers everything
2. `stores={"sessions": MemoryStore()}` — provides the session store

- `exclude` paths skip auth entirely (no `retrieve_user_handler` call, `request.user` not populated)
- Individual routes can also opt out with `opt={"exclude_from_auth": True}`. On routes already in the `exclude` list, `opt` is redundant but provides defense-in-depth. Use the `exclude` list as the single source of truth for path-level exclusions.
- `alchemy_config` is the `SQLAlchemyAsyncConfig` already defined in app.py from story 1.1. The `retrieve_user_handler` uses `alchemy_config.get_session()` for a managed DB session.

### Login/Logout Controller Pattern

```python
# In AuthController (src/easyorario/controllers/auth.py)
from litestar import get, post, Request
from litestar.response import Template, Redirect

@get("/accedi")
async def show_login(self, request: Request) -> Template:
    # Support cross-redirect success messages from registration (query param approach)
    msg = request.query_params.get("msg")
    success = MESSAGES.get(msg) if msg else None
    return Template(template_name="pages/login.html", context={"success": success})

@post("/accedi")
async def login(self, request: Request, auth_service: AuthService) -> Template | Redirect:
    data = await request.form()
    email = data.get("email", "")
    password = data.get("password", "")
    try:
        user = await auth_service.authenticate_user(email, password)
        request.set_session({"user_id": str(user.id)})
        # Flash success message (implementation depends on flash mechanism)
        return Redirect(path="/dashboard")
    except InvalidCredentialsError:
        return Template(
            template_name="pages/login.html",
            context={"error": ERRORS["invalid_credentials"], "email_value": email},
        )

@post("/esci")
async def logout(self, request: Request) -> Redirect:
    request.clear_session()
    return Redirect(path="/accedi?msg=logout_success")
```

**Form data parsing:** Use `request.form()` to extract form data for server-rendered forms. This returns a multidict.

### Login Template (Oat UI)

```html
<!-- templates/pages/login.html -->
{% extends "base.html" %}
{% block content %}
<div class="container">
  <div class="row">
    <div class="col-6 offset-3">
      <h1>Accedi</h1>

      {% if success %}
      <div role="alert" data-variant="success">{{ success }}</div>
      {% endif %}

      {% if error %}
      <div role="alert" data-variant="error">{{ error }}</div>
      {% endif %}

      <form method="post" action="/accedi">
        {{ csrf_input | safe }}

        <label data-field>
          Email
          <input type="email" name="email" required placeholder="nome@esempio.it"
                 value="{{ email_value | default('') }}">
        </label>

        <label data-field>
          Password
          <input type="password" name="password" required>
        </label>

        <button type="submit">Accedi</button>
      </form>

      <p>Non hai un account? <a href="/registrati">Registrati</a></p>
    </div>
  </div>
</div>
{% endblock %}
```

### Auth Guard Pattern

```python
# src/easyorario/guards/auth.py
from litestar.connection import ASGIConnection
from litestar.handlers import BaseRouteHandler
from litestar.exceptions import NotAuthorizedException


def requires_login(connection: ASGIConnection, _: BaseRouteHandler) -> None:
    """Ensure user is authenticated."""
    if not connection.user:
        raise NotAuthorizedException(detail="Login required")


def requires_role(connection: ASGIConnection, handler: BaseRouteHandler) -> None:
    """Ensure user has the required role (set via handler opt)."""
    required_role = handler.opt.get("required_role")
    if required_role and (not connection.user or connection.user.role != required_role):
        raise NotAuthorizedException(detail="Insufficient permissions")
```

**Note:** `SessionAuth` already rejects unauthenticated requests to non-excluded routes by returning 401. The `requires_login` guard is an additional explicit check. The `requires_role` guard is the main value-add here — it enforces role-based access per-route.

### Error Handling for Login

Add to `exceptions.py`:
```python
class InvalidCredentialsError(EasyorarioError):
    """Raised when login credentials are invalid."""
```

**Security note:** Always use a generic "Email o password non validi" message — never reveal whether the email exists or the password is wrong specifically. This prevents user enumeration.

### Flash Messages Strategy (Definitive for PoC)

**Use URL query parameters for cross-redirect success messages and template context for inline errors.**

- Errors on the same page: pass `error` variable in template context (e.g., invalid credentials)
- Success after redirect: use query params (e.g., `/accedi?msg=registration_success`, `/accedi?msg=logout_success`)
- The receiving controller reads the `msg` query param, looks up the Italian message from `i18n/errors.py`, and passes it as `success` context variable

```python
# In show_login handler:
MESSAGES = {
    "registration_success": "Registrazione completata. Effettua l'accesso.",
    "logout_success": "Disconnessione effettuata.",
}
msg = request.query_params.get("msg")
success = MESSAGES.get(msg) if msg else None
```

This avoids the complexity of session-based flash plugins. Do NOT implement `set_flash`/`get_flash` helpers for the PoC.

### Architecture Deviation: Session Store

The architecture doc specifies "DB-backed cookie sessions." This story uses `MemoryStore()` for simplicity in the PoC sprint. Sessions will be lost on server restart. This is acceptable for local development and demo purposes. To upgrade later:
- Replace `MemoryStore()` with `FileStore(path=Path("./session_data"))` for persistence across restarts
- Or implement a custom SQLAlchemy-backed store for full architecture compliance
This should be addressed before any deployment beyond local development.

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

### Test Fixtures for Authenticated Routes

```python
# tests/conftest.py additions
import pytest
from httpx import AsyncClient

@pytest.fixture
async def registered_user(async_session):
    """Create a user in the DB for login tests."""
    from easyorario.services.auth import hash_password
    from easyorario.models.user import User
    user = User(
        email="test@esempio.it",
        hashed_password=hash_password("password123"),
        role="responsible_professor",
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user

@pytest.fixture
async def authenticated_client(test_client, registered_user):
    """Test client with an active session (logged-in user)."""
    # First, GET the login page to obtain a CSRF token cookie
    get_response = await test_client.get("/accedi")
    csrf_token = get_response.cookies.get("csrftoken", "")
    # Then POST login with the valid CSRF token
    response = await test_client.post("/accedi", data={
        "email": registered_user.email,
        "password": "password123",
        "_csrf_token": csrf_token,
    })
    assert response.status_code in (302, 303)  # Verify login succeeded
    return test_client
```

### Project Structure Notes

Directories to CREATE:
```
tests/guards/                              (CREATE directory)
```

Files to CREATE in this story:
```
src/easyorario/guards/auth.py              (CREATE)
src/easyorario/controllers/dashboard.py    (CREATE — minimal placeholder)
templates/pages/login.html                 (CREATE)
templates/pages/dashboard.html             (CREATE — minimal placeholder)
tests/guards/test_auth_guard.py            (CREATE)
```

Files to UPDATE:
```
src/easyorario/app.py                      (UPDATE: add SessionAuth, on_app_init, stores, exclude paths)
src/easyorario/config.py                   (UPDATE: add SESSION_SECRET if needed for cookie signing)
src/easyorario/exceptions.py               (UPDATE: add InvalidCredentialsError)
src/easyorario/services/auth.py            (UPDATE: add authenticate_user method)
src/easyorario/controllers/auth.py         (UPDATE: add GET/POST /accedi, POST /esci)
src/easyorario/i18n/errors.py              (UPDATE: add login/logout messages)
src/easyorario/guards/__init__.py          (UPDATE: export requires_login, requires_role)
tests/conftest.py                          (UPDATE: add registered_user, authenticated_client fixtures)
tests/services/test_auth.py               (UPDATE: add authenticate_user tests)
tests/controllers/test_auth.py            (UPDATE: add login/logout tests)
```

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.3]
- [Source: _bmad-output/planning-artifacts/architecture.md#Authentication & Security]
- [Source: _bmad-output/planning-artifacts/architecture.md#API & Communication Patterns]
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns & Consistency Rules]
- [Source: _bmad-output/planning-artifacts/architecture.md#Architectural Boundaries]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Page Map & User Journeys]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Design System]
- [Source: _bmad-output/implementation-artifacts/1-1-project-skeleton-development-infrastructure.md — Previous story context]
- [Source: _bmad-output/implementation-artifacts/1-2-user-registration.md — Previous story context]
- [Source: docs/PRD.md#FR-11, FR-12]
- [Source: Litestar docs — Security Backends (session auth)]
- [Source: Litestar docs — Guards]
- [Source: Litestar docs — Built-in Middleware (CSRF, Sessions)]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
