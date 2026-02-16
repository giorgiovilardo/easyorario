# Story 1.4: Dashboard & Role-Based Access Control

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a logged-in user,
I want to see a personalized dashboard,
so that I can view my timetables and access features appropriate to my role.

## Acceptance Criteria

1. **Given** I am logged in as a Responsible Professor **When** I visit `/dashboard` **Then** I see my timetables list (empty state with "Nuovo Orario" button for now)

2. **Given** I am logged in as a Professor **When** I visit `/dashboard` **Then** I see timetables I have previously accessed via shared links (empty state for now — access tracking implemented in Epic 5) **And** I do not see the "Nuovo Orario" button

3. **Given** I am a Professor **When** I attempt to access a Responsible Professor-only action (e.g., future `/orario/nuovo`) **Then** I receive a 403 Forbidden response

4. **Given** I am unauthenticated **When** I attempt to access `/dashboard` or any draft timetable URL **Then** I receive a 401 and am redirected to `/accedi`

5. **Given** I am authenticated and visit `/` **When** the page loads **Then** I am redirected to `/dashboard`

## Tasks / Subtasks

- [ ] Task 1: Upgrade placeholder dashboard controller to full implementation (AC: #1, #2, #5)
  - [ ] 1.1 Update `src/easyorario/controllers/dashboard.py` — replace placeholder with role-aware logic
  - [ ] 1.2 `GET /dashboard` — query user's timetables (empty for now, no Timetable model yet)
  - [ ] 1.3 Pass `user` object and role to template context for conditional rendering
  - [ ] 1.4 Inject `request.user` via Litestar's connection scope (populated by SessionAuth)

- [ ] Task 2: Upgrade placeholder dashboard template to role-aware UI (AC: #1, #2)
  - [ ] 2.1 Update `templates/pages/dashboard.html` — extending `base.html`
  - [ ] 2.2 Display user greeting with email (e.g., "Benvenuto, nome@esempio.it")
  - [ ] 2.3 Conditional: if role == "responsible_professor", show "Nuovo Orario" button (links to `/orario/nuovo` — non-functional until Epic 2)
  - [ ] 2.4 Conditional: if role == "professor", show "Orari condivisi" heading with empty state text ("Nessun orario condiviso ancora")
  - [ ] 2.5 Timetable list area with empty state: "Nessun orario creato ancora. Crea il tuo primo orario!" (for Responsible Professor)
  - [ ] 2.6 Use Oat UI semantic elements: headings, buttons, alert for empty state

- [ ] Task 3: Update home page to redirect authenticated users (AC: #5)
  - [ ] 3.1 Update `src/easyorario/controllers/home.py` — `GET /` checks if user is authenticated
  - [ ] 3.2 If authenticated: redirect to `/dashboard`
  - [ ] 3.3 If not authenticated: render the existing index.html (or redirect to `/accedi`)
  - [ ] 3.4 Ensure `/` is in SessionAuth `exclude` list so it doesn't 401 for unauthenticated users

- [ ] Task 4: Apply role-based guards to routes (AC: #3, #4)
  - [ ] 4.1 Apply `requires_role` guard to dashboard controller with role checks where needed
  - [ ] 4.2 Create `src/easyorario/guards/roles.py` with standalone `requires_responsible_professor` guard:
    ```python
    def requires_responsible_professor(connection: ASGIConnection, _: BaseRouteHandler) -> None:
        if not connection.user or connection.user.role != "responsible_professor":
            raise NotAuthorizedException(detail="Insufficient permissions")
    ```
  - [ ] 4.3 Apply `requires_responsible_professor` guard to future Responsible Professor-only routes (placeholder: register it on a test-only dummy route for now to verify the guard works)
  - [ ] 4.4 Verify SessionAuth already protects `/dashboard` (not in `exclude` list)

- [ ] Task 5: Create Italian 403 error page and exception handler (AC: #3)
  - [ ] 5.1 Create `templates/pages/errors/403.html` — Italian forbidden message ("Accesso non autorizzato. Non hai i permessi per questa azione.")
  - [ ] 5.2 Register Litestar exception handler for `NotAuthorizedException` (403) to render the Italian error template
  - [ ] 5.3 Update `src/easyorario/i18n/errors.py` with: `forbidden`: "Non hai i permessi per accedere a questa risorsa"

- [ ] Task 6: Create Italian 401 redirect handler (AC: #4)
  - [ ] 6.1 Register Litestar exception handler for 401 `NotAuthorizedException` to redirect to `/accedi`
  - [ ] 6.2 Distinguish 401 (not authenticated → redirect) from 403 (authenticated but wrong role → error page)
  - [ ] 6.3 Update `src/easyorario/i18n/errors.py` with: `login_required`: "Effettua l'accesso per continuare" (may already exist from story 1.3)

- [ ] Task 7: Add logout button to base template nav (AC: #1, #2)
  - [ ] 7.1 Update `templates/base.html` — add nav bar with conditional content
  - [ ] 7.2 If authenticated: show user email, link to `/dashboard`, and "Esci" (logout) button as `POST /esci` form
  - [ ] 7.3 If not authenticated: show "Accedi" and "Registrati" links
  - [ ] 7.4 Use Oat UI `<nav>` semantic styling

- [ ] Task 8: Write tests (AC: #1, #2, #3, #4, #5)
  - [ ] 8.1 `tests/controllers/test_dashboard.py`:
    - `test_get_dashboard_as_responsible_professor_returns_200_with_nuovo_orario_button`
    - `test_get_dashboard_as_professor_returns_200_without_nuovo_orario_button`
    - `test_get_dashboard_unauthenticated_redirects_to_accedi`
  - [ ] 8.2 `tests/controllers/test_home.py` (update existing):
    - `test_get_home_authenticated_redirects_to_dashboard`
    - `test_get_home_unauthenticated_renders_index`
  - [ ] 8.3 `tests/guards/test_auth_guard.py` (update existing from story 1.3):
    - `test_requires_responsible_professor_with_professor_role_returns_403`
    - `test_requires_responsible_professor_with_responsible_professor_role_succeeds`
  - [ ] 8.4 `tests/controllers/test_error_handlers.py`:
    - `test_unauthenticated_access_redirects_to_accedi`
    - `test_unauthorized_role_access_returns_403_with_italian_message`

## Dev Notes

### Architecture Patterns & Constraints

- **Layered architecture applies:** DashboardController (HTTP) → no service layer needed for this story (dashboard just queries user context and renders). When Timetable model exists (Epic 2), a TimetableService will be injected.
- **Dependency injection:** Use Litestar's DI. The `request.user` is populated automatically by `SessionAuth` middleware (configured in story 1.3). Access via `request.user` in controller methods.
- **Guards enforce authorization declaratively:** Controllers never check `request.user.role` directly for access control. Use guards on route handlers. However, for template-level conditional rendering (show/hide button), reading `request.user.role` in the controller and passing to template context is correct.
- **Italian-only user-facing text:** All UI text, error messages, empty states in Italian. Code and logs in English.
- **No Timetable model yet:** The dashboard will show empty state for now. Timetable CRUD is Epic 2. Do NOT create a Timetable model in this story.
- **`/dashboard` path is English by design** (per UX specification site map). Do NOT rename to an Italian equivalent. The Italian naming convention applies to user-facing workflow pages (`/accedi`, `/registrati`, `/orario/...`) but `/dashboard` is retained as a universally understood loanword in Italian web applications.

### Auth Mechanism Decision Matrix

| Scenario | Mechanism | Example |
|---|---|---|
| Public page (no auth needed) | Add to SessionAuth `exclude` list | `/`, `/accedi`, `/health` |
| Auth required, any role | SessionAuth handles it (route NOT in exclude) | `/dashboard` |
| Auth required, specific role | Add `guards=[requires_role]` + `opt={"required_role": "..."}` | `/orario/nuovo` (future) |

**Note:** `requires_login` guard is defined for completeness but is never needed on non-excluded routes because SessionAuth already rejects unauthenticated requests with 401. Do NOT add it redundantly.

### Professor Role Assignment

Professor users cannot be created through the registration UI (all registrations default to `responsible_professor`). For the PoC, Professor users are created via: (1) direct database manipulation, (2) test fixtures, or (3) a future admin interface. This is an intentional simplification. Story 5.2 implies Professors gain access via shared links, at which point a Professor account creation flow may be needed.

### Previous Stories Established

**Story 1.1 created:**
- `src/easyorario/app.py` — Litestar app factory with plugins, middleware, route handlers
- `src/easyorario/config.py` — Settings from env vars
- `src/easyorario/exceptions.py` — `EasyorarioError` base class
- `src/easyorario/models/base.py` — SQLAlchemy declarative base
- `src/easyorario/controllers/health.py` — `GET /health`
- `src/easyorario/controllers/home.py` — `GET /` renders index.html
- `templates/base.html` — Base layout with Oat UI CDN includes
- `templates/pages/index.html` — Minimal home page
- `tests/conftest.py` — Test client fixture, test DB
- `justfile`, `Dockerfile`, `alembic/`, `structlog` configured

**Story 1.2 created:**
- `src/easyorario/models/user.py` — User model (id, email, hashed_password, role, created_at)
- `src/easyorario/repositories/user.py` — UserRepository with `get_by_email()`
- `src/easyorario/services/auth.py` — AuthService with `hash_password()`, `verify_password()`, `register_user()`
- `src/easyorario/controllers/auth.py` — AuthController with `GET/POST /registrati`
- `src/easyorario/i18n/errors.py` — Italian error messages for registration
- `src/easyorario/exceptions.py` — Updated: `EmailAlreadyTakenError`, `PasswordTooShortError`
- `templates/pages/register.html` — Registration form
- `templates/partials/flash_messages.html` — Reusable flash message partial
- CSRF middleware configured in `app.py`

**Story 1.3 created:**
- `src/easyorario/app.py` — Updated: SessionAuth with `retrieve_user_handler`, `on_app_init`, `stores`, `exclude` paths
- `src/easyorario/services/auth.py` — Updated: `authenticate_user()` method
- `src/easyorario/controllers/auth.py` — Updated: `GET/POST /accedi`, `POST /esci`
- `src/easyorario/guards/auth.py` — `requires_login()`, `requires_role()` guards
- `src/easyorario/exceptions.py` — Updated: `InvalidCredentialsError`
- `src/easyorario/i18n/errors.py` — Updated: `invalid_credentials`, `login_required`, `logout_success`
- `templates/pages/login.html` — Login form
- `src/easyorario/controllers/dashboard.py` — **Minimal placeholder** (just renders heading + user email)
- `templates/pages/dashboard.html` — **Minimal placeholder** (just heading + email)
- `tests/conftest.py` — Updated: `registered_user`, `authenticated_client` fixtures

### Technical Requirements

**SessionAuth & User Access Pattern:**

The `request.user` object is a `User` model instance (or `None` for excluded routes). It is populated by `retrieve_user_handler` in `app.py` which reads `user_id` from the session dict and loads the User from the database. For dashboard:

```python
# In controller method — user is guaranteed non-None on protected routes
@get("/dashboard")
async def get_dashboard(self, request: Request) -> Template:
    user = request.user  # User model instance, populated by SessionAuth
    return Template(
        template_name="pages/dashboard.html",
        context={
            "user": user,
            "is_responsible": user.role == "responsible_professor",
        },
    )
```

**401 vs 403 Distinction:**

Litestar's `SessionAuth` automatically returns 401 for unauthenticated requests to non-excluded routes. To customize this behavior (redirect to `/accedi` instead of bare 401), register an exception handler:

```python
from litestar.exceptions import NotAuthorizedException
from litestar.response import Redirect, Template
from litestar import Request

async def handle_not_authorized(request: Request, exc: NotAuthorizedException) -> Redirect | Template:
    # Use getattr to safely access request.user — on unauthenticated requests,
    # SessionAuth may raise the exception BEFORE populating scope["user"],
    # so request.user could raise AttributeError or return an Empty sentinel.
    user = getattr(request, "user", None)
    if not user:
        # 401: Not authenticated → redirect to login
        return Redirect(path="/accedi")
    else:
        # 403: Authenticated but wrong role → show error page
        return Template(
            template_name="pages/errors/403.html",
            context={"error": ERRORS["forbidden"], "user": user},
            status_code=403,
        )
```

Register in app factory:
```python
app = Litestar(
    exception_handlers={NotAuthorizedException: handle_not_authorized},
    ...
)
```

**Home Page Redirect for Authenticated Users:**

The `/` route is in SessionAuth's `exclude` list (from story 1.3), so `request.user` is NOT populated. To check auth on an excluded route, inspect the session directly. **Important:** Whether `request.session` is populated on excluded routes depends on Litestar version — the session middleware may or may not run on excluded routes. Write a test first (TDD) to verify behavior.

```python
@get("/")
async def home(self, request: Request) -> Template | Redirect:
    # On excluded routes, request.user is not set. Check session directly.
    user_id = request.session.get("user_id") if hasattr(request, "session") and request.session else None
    if user_id:
        return Redirect(path="/dashboard")
    return Template(template_name="pages/index.html")
```

**Fallback if `request.session` is not available on excluded routes:** Remove `/` from the exclude list and use the standard auth flow. The home controller would then check `request.user` (which would be `None` for unauthenticated since `retrieve_user_handler` returns `None` when session has no `user_id`).

**Role Guard Application Pattern:**

The `requires_role` guard from story 1.3 reads `required_role` from `handler.opt`. Apply it to routes:

```python
from easyorario.guards.auth import requires_role

# On a specific route that requires responsible_professor role:
@get("/orario/nuovo", guards=[requires_role], opt={"required_role": "responsible_professor"})
async def create_timetable(self, ...) -> Template:
    ...
```

For this story, the dashboard itself is accessible to both roles (different content rendered). The guard is needed for Responsible Professor-only actions. Since `/orario/nuovo` doesn't exist yet, verify the guard works via tests.

### Architecture Compliance

**Boundary Rules — MUST follow:**

| Rule | This Story's Application |
|---|---|
| Controller → Service → Repository (one-way) | Dashboard controller has no service/repo dependency yet. When Timetable model is added in Epic 2, inject TimetableService. Do NOT query DB directly from controller. |
| Controllers handle HTTP only — no business logic | Controller reads `request.user`, passes data to template. No role-checking logic beyond what guards provide. |
| Guards enforce authorization declaratively | Use `requires_role` guard on role-restricted routes. Dashboard route itself has no guard (both roles access it) — conditional rendering in template handles role differences. |
| Italian user-facing text, English code/logs | All template text in Italian. All Python identifiers, comments, log messages in English. |
| `structlog` for all logging, never `print()` | Log access attempts if needed via structlog. |
| Use Litestar DI, never manual instantiation | If any service is needed, inject via Litestar's `Provide` / type-hint DI. |
| `snake_case` for Python/JSON, `kebab-case` for URLs | Dashboard URL is `/dashboard` (no kebab needed). Template filenames: `dashboard.html`. |
| `jj` for VCS, never raw `git` | All commits via `jj new`, `jj describe`, `jj commit`. |

**Anti-Patterns — NEVER do:**

- Do NOT hardcode Italian strings in Python code — use template text or `i18n/errors.py` message mappings
- Do NOT check `request.user.role` in the controller for access control — use guards. (Reading role for template context is fine.)
- Do NOT create a Timetable model, migration, or any Epic 2+ code in this story
- Do NOT add any middleware manually that SessionAuth already handles
- Do NOT use bare `except:` or catch `Exception` without re-raising
- Do NOT use `git` commands — use `jj` exclusively

### Library & Framework Requirements

**Litestar (>=2.21.0) — Key APIs for this story:**

| API | Usage | Import |
|---|---|---|
| `Request.user` | Access authenticated User instance | `from litestar import Request` |
| `Request.session` | Read session dict on excluded routes | `from litestar import Request` |
| `Template` | Render Jinja2 template response | `from litestar.response import Template` |
| `Redirect` | HTTP redirect response | `from litestar.response import Redirect` |
| `Controller` | Base class for route controllers | `from litestar import Controller` |
| `get`, `post` | Route decorators | `from litestar import get, post` |
| `NotAuthorizedException` | 401/403 exception | `from litestar.exceptions import NotAuthorizedException` |
| `exception_handlers` | App-level exception handler dict | Litestar app constructor param |
| `guards` | Route-level guard list | Route decorator param: `guards=[fn]` |
| `opt` | Route metadata dict for guards | Route decorator param: `opt={...}` |

**Litestar Exception Handlers:**

Exception handlers are registered at the app level as a dict mapping exception classes to handler callables. The handler receives `(request, exc)` and must return a `Response`:

```python
app = Litestar(
    exception_handlers={
        NotAuthorizedException: handle_not_authorized,
    },
)
```

**Oat UI — Components used in this story:**

| Component | HTML | Usage |
|---|---|---|
| Nav | `<nav>` | Top navigation bar with auth-conditional links |
| Button | `<button>` / `<a>` with button styling | "Nuovo Orario" CTA, "Esci" logout |
| Alert | `<div role="alert">` | Empty state messages |
| Grid | Oat 12-column grid classes | Dashboard layout |
| Badge | `<span data-badge>` or equivalent | Role indicator (optional) |

**Oat UI nav pattern:**
```html
<nav>
  <a href="/dashboard"><strong>Easyorario</strong></a>
  <span style="flex-grow:1"></span>
  {% if user %}
    <span>{{ user.email }}</span>
    <form method="post" action="/esci" style="display:inline">
      {{ csrf_input | safe }}
      <button type="submit">Esci</button>
    </form>
  {% else %}
    <a href="/accedi">Accedi</a>
    <a href="/registrati">Registrati</a>
  {% endif %}
</nav>
```

**Jinja2 — Template globals needed:**

For the nav bar to work on all pages, the `user` object must be available as a template global (or passed in every template context). Two approaches:

1. **Template global via middleware/hook:** Register a `before_request` hook that adds `user` to template context automatically.
2. **Pass in every controller:** Each controller passes `request.user` in template context.

**Recommended for PoC:** Pass explicitly in each controller. Simpler, no magic. The nav bar partial can check `{% if user %}` since all controllers pass it.

**TECH DEBT:** Every controller must pass `user=request.user` (or `user=getattr(request, "user", None)` on excluded routes) in template context for the nav bar. This is acceptable for Sprint 1 (4 controllers) but must be refactored to a template global or `before_request` hook before Epic 2 adds more controllers.

**No new dependencies required for this story.** Everything is already in `pyproject.toml` from stories 1.1-1.3.

### File Structure Requirements

**Files to UPDATE (exist from previous stories):**

```
src/easyorario/app.py                      (UPDATE: add exception_handlers for 401/403)
src/easyorario/controllers/home.py         (UPDATE: add auth check + redirect to /dashboard)
src/easyorario/controllers/dashboard.py    (UPDATE: replace placeholder with role-aware logic)
src/easyorario/guards/auth.py              (UPDATE: add requires_responsible_professor convenience guard if needed)
src/easyorario/i18n/errors.py              (UPDATE: add forbidden, empty state messages)
templates/base.html                        (UPDATE: add <nav> bar with auth-conditional links)
templates/pages/dashboard.html             (UPDATE: replace placeholder with role-aware template)
tests/conftest.py                          (UPDATE: add professor_user fixture, authenticated_professor_client)
tests/controllers/test_home.py             (UPDATE: add redirect tests for authenticated users)
```

**Files to CREATE:**

```
templates/pages/errors/403.html            (CREATE: Italian 403 forbidden page)
tests/controllers/test_dashboard.py        (CREATE: dashboard role-based tests)
tests/controllers/test_error_handlers.py   (CREATE: 401 redirect + 403 error page tests)
```

**Files NOT to touch:**

```
src/easyorario/models/*                    (NO CHANGE: No new models in this story)
src/easyorario/repositories/*              (NO CHANGE: No new repos)
src/easyorario/services/*                  (NO CHANGE: No service logic needed)
alembic/versions/*                         (NO CHANGE: No migrations)
pyproject.toml                             (NO CHANGE: No new dependencies)
```

**Directory creation needed:**

```
templates/pages/errors/                    (CREATE directory: for error page templates)
```

### Testing Requirements

**TDD Workflow — Mandatory:**

1. **Red:** Write a small, focused test that fails
2. **Green:** Write minimum code to make it pass
3. **Refactor/Tidy:** Clean up only if needed, all tests stay green
4. **Repeat**

Test naming: `test_{action}_{condition}_{expected_result}`

**Test Fixtures Needed (update `tests/conftest.py`):**

```python
@pytest.fixture
async def professor_user(async_session):
    """Create a Professor user (read + comment only, no create permissions)."""
    from easyorario.services.auth import hash_password
    from easyorario.models.user import User
    user = User(
        email="prof@esempio.it",
        hashed_password=hash_password("password123"),
        role="professor",
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user

@pytest.fixture
async def authenticated_professor_client(test_client, professor_user):
    """Test client logged in as a Professor (not Responsible Professor)."""
    response = await test_client.post("/accedi", data={
        "email": professor_user.email,
        "password": "password123",
        "_csrf_token": "...",  # extract from cookie/response
    })
    return test_client
```

**Existing fixtures from story 1.3 to reuse:**
- `registered_user` — creates a `responsible_professor` role user
- `authenticated_client` — test client logged in as Responsible Professor

**Required Test Cases:**

| Test File | Test Name | Verifies |
|---|---|---|
| `test_dashboard.py` | `test_get_dashboard_as_responsible_professor_returns_200_with_nuovo_orario_button` | AC #1: RP sees "Nuovo Orario" |
| `test_dashboard.py` | `test_get_dashboard_as_professor_returns_200_without_nuovo_orario_button` | AC #2: Prof doesn't see "Nuovo Orario" |
| `test_dashboard.py` | `test_get_dashboard_as_professor_shows_shared_timetables_empty_state` | AC #2: Prof sees "Nessun orario condiviso" |
| `test_dashboard.py` | `test_get_dashboard_unauthenticated_redirects_to_accedi` | AC #4: 401 → redirect |
| `test_home.py` | `test_get_home_authenticated_redirects_to_dashboard` | AC #5: `/` → `/dashboard` |
| `test_home.py` | `test_get_home_unauthenticated_renders_index` | AC #5: `/` shows index when not logged in |
| `test_auth_guard.py` | `test_requires_responsible_professor_with_professor_role_returns_403` | AC #3: role guard blocks Professor |
| `test_auth_guard.py` | `test_requires_responsible_professor_with_correct_role_succeeds` | AC #3: role guard allows RP |
| `test_error_handlers.py` | `test_unauthenticated_access_to_protected_route_redirects_to_accedi` | AC #4: 401 redirect handler |
| `test_error_handlers.py` | `test_unauthorized_role_returns_403_with_italian_message` | AC #3: 403 shows Italian error |

**Testing the 401 redirect:**

SessionAuth returns 401 for unauthenticated requests to non-excluded routes. The exception handler should intercept this and redirect. Test by making an unauthenticated GET to `/dashboard` and asserting a 302 redirect to `/accedi`:

```python
async def test_unauthenticated_access_to_protected_route_redirects_to_accedi(test_client):
    response = await test_client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/accedi"
```

**Testing role-based template content:**

Assert on HTML content to verify conditional rendering:

```python
async def test_get_dashboard_as_responsible_professor_returns_200_with_nuovo_orario_button(
    authenticated_client,
):
    response = await authenticated_client.get("/dashboard")
    assert response.status_code == 200
    assert "Nuovo Orario" in response.text

async def test_get_dashboard_as_professor_returns_200_without_nuovo_orario_button(
    authenticated_professor_client,
):
    response = await authenticated_professor_client.get("/dashboard")
    assert response.status_code == 200
    assert "Nuovo Orario" not in response.text
```

### Previous Story Intelligence

**From Story 1.3 (User Login & Session Management) — Direct predecessor:**

Key patterns established that this story MUST follow:
- **SessionAuth is configured in `app.py`** with `on_app_init`, `exclude` paths, and `MemoryStore` for sessions. Do NOT reconfigure or duplicate.
- **`exclude` list** currently contains: `["/", "/accedi", "/registrati", "/health", "/static/", "/schema"]`. Do NOT remove any existing excludes.
- **Guards defined in `src/easyorario/guards/auth.py`**: `requires_login` and `requires_role`. These are defined but not yet applied to any route. This story is where `requires_role` gets its first real application.
- **Placeholder dashboard** exists at `src/easyorario/controllers/dashboard.py` and `templates/pages/dashboard.html`. These are minimal — just a heading and user email. This story replaces them with full role-aware implementations.
- **Flash messages approach:** Story 1.3 recommended template context for errors and URL query params for success redirects. Flash helper functions (`set_flash`, `get_flash`) were documented but may or may not have been implemented. Check what exists before building on it.
- **`POST /esci` logout** exists in AuthController. The nav bar logout button should POST to this endpoint with CSRF token.
- **`authenticated_client` fixture** exists in conftest.py — logs in as `responsible_professor` role.

**From Story 1.2 (User Registration):**

- **User model role field** defaults to `"responsible_professor"`. There is no UI for selecting Professor role during registration. For testing, create Professor users directly via fixture (set `role="professor"`).
- **CSRF middleware** is active — all POST forms must include `_csrf_token` hidden input. The logout form in the nav bar needs this.

**From Story 1.1 (Project Skeleton):**

- **`GET /` in `controllers/home.py`** renders `index.html`. This story modifies it to redirect authenticated users to `/dashboard`.
- **`templates/base.html`** has Oat UI CDN includes but no nav bar yet. This story adds the nav bar.
- **Static files** served from `static/` directory. `app.css` exists but is empty/minimal.

### Git Intelligence

**Recent commits (all BMAD planning — no implementation code yet):**

```
c2e2e9e BMAD phase 5: sprint plan
cdc3cb2 BMAD phase 4: IR
0de6e06 BMAD phase 3: create epics
d439d32 BMAD UX design done
1d7b052 BMAD phase 2: bmad-bmm-create-architecture
fc76d17 BMAD phase 1
6f2afe8 add PRD before BMAD
37b676d add some libraries
97715f6 first commit
```

**Implications:**
- No implementation code exists yet. Stories 1-1, 1-2, 1-3 are `ready-for-dev` but not implemented.
- This story (1.4) depends on stories 1.1-1.3 being implemented first. The dev agent for 1.4 can assume those stories are complete and their files exist.
- The `pyproject.toml` already has core dependencies declared (commit `37b676d`).
- VCS is `jj` (Jujutsu) — the dev agent MUST use `jj` commands, never `git` directly.

### Project Context Reference

No `project-context.md` file exists yet. Context is derived from:
- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.4]
- [Source: _bmad-output/planning-artifacts/architecture.md#Authentication & Security]
- [Source: _bmad-output/planning-artifacts/architecture.md#API & Communication Patterns]
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns & Consistency Rules]
- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure & Boundaries]
- [Source: _bmad-output/planning-artifacts/architecture.md#Architectural Boundaries]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Page Map & User Journeys]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Design System]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Key Interaction Patterns]
- [Source: _bmad-output/implementation-artifacts/1-1-project-skeleton-development-infrastructure.md]
- [Source: _bmad-output/implementation-artifacts/1-2-user-registration.md]
- [Source: _bmad-output/implementation-artifacts/1-3-user-login-session-management.md]
- [Source: docs/PRD.md#FR-11, FR-12, NFR-6]

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

### Dashboard Template (Oat UI)

```html
<!-- templates/pages/dashboard.html -->
{% extends "base.html" %}
{% block content %}
<div class="container">
  <div class="row">
    <div class="col-12">
      <h1>Dashboard</h1>
      <p>Benvenuto, {{ user.email }}</p>

      {% if is_responsible %}
        <section>
          <h2>I miei orari</h2>
          <!-- Empty state for now — timetable list comes in Epic 2 -->
          <div role="alert">
            Nessun orario creato ancora. Crea il tuo primo orario!
          </div>
          <a href="/orario/nuovo"><button>Nuovo Orario</button></a>
        </section>
      {% else %}
        <section>
          <h2>Orari condivisi</h2>
          <!-- Empty state — shared timetable tracking comes in Epic 5 -->
          <div role="alert">
            Nessun orario condiviso ancora.
          </div>
        </section>
      {% endif %}
    </div>
  </div>
</div>
{% endblock %}
```

### 403 Error Template

```html
<!-- templates/pages/errors/403.html -->
{% extends "base.html" %}
{% block content %}
<div class="container">
  <div class="row">
    <div class="col-6 offset-3">
      <h1>Accesso negato</h1>
      <div role="alert" data-variant="error">
        {{ error | default("Non hai i permessi per accedere a questa risorsa.") }}
      </div>
      <a href="/dashboard">Torna alla dashboard</a>
    </div>
  </div>
</div>
{% endblock %}
```

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
