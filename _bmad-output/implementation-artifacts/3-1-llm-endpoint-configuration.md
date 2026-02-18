# Story 3.1: LLM Endpoint Configuration

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a Responsible Professor,
I want to configure my LLM API endpoint,
so that the system can translate my constraints using my preferred AI provider.

## Acceptance Criteria

1. **Given** I am logged in as a Responsible Professor **When** I visit `/impostazioni` **Then** I see a form with fields for: LLM API base URL, API key (password-masked input), and model identifier

2. **Given** I am on `/impostazioni` **When** I submit a valid LLM configuration (reachable URL, valid API key, valid model) **Then** the system validates connectivity with a test request to the endpoint, stores the configuration in my HTTP session (NOT persisted to DB), and I see an Italian success message ("Configurazione LLM salvata con successo")

3. **Given** I submit an invalid LLM configuration (unreachable URL, bad API key, or connection error) **When** the system attempts the test request **Then** I see an Italian error message explaining the failure (e.g., "Impossibile connettersi all'endpoint LLM" or "Chiave API non valida") and the form is re-rendered with my submitted values (except the API key)

4. **Given** I have not configured an LLM endpoint in my session **When** I try to trigger constraint translation (Epic 3 Story 3.2 — non-functional yet, but the guard must exist) **Then** I am redirected to `/impostazioni` with an Italian flash message ("Configura l'endpoint LLM prima di procedere")

5. **Given** I have already configured an LLM endpoint in my session **When** I visit `/impostazioni` again **Then** the form is pre-populated with my saved base URL and model identifier (API key is NOT shown — user must re-enter to change it)

6. **Given** I am a Professor (not Responsible Professor) **When** I try to access `/impostazioni` **Then** I receive a 403 Forbidden response

7. **Given** I submit the form with missing required fields (empty base URL or empty API key) **When** the form is processed **Then** I see an Italian validation error and remain on the form page with previously entered values preserved

8. **Given** the test request to the LLM endpoint takes too long **When** a 10-second timeout is exceeded **Then** I see an Italian error message about the timeout ("Timeout durante il test di connessione")

## Tasks / Subtasks

- [x] Task 1: Add httpx as explicit dependency (AC: #2, #3, #8)
  - [x] 1.1 Add `httpx>=0.28.0` to `pyproject.toml` dependencies (httpx is already available via `litestar[standard]` but the LLM service imports it directly, so declare it explicitly)
  - [x] 1.2 Run `uv sync` to update lockfile

- [x] Task 2: Add LLM domain exceptions and Italian messages (AC: #3, #7, #8)
  - [x] 2.1 Add `LLMConfigError` (base for LLM config errors, accepts `error_key`) to `easyorario/exceptions.py`
  - [x] 2.2 Add Italian messages to `easyorario/i18n/errors.py`: `llm_connection_failed`, `llm_auth_failed`, `llm_timeout`, `llm_base_url_required`, `llm_api_key_required`, `llm_config_saved`, `llm_config_required`

- [x] Task 3: Create LLM service with connectivity test (AC: #2, #3, #8)
  - [x] 3.1 Create `easyorario/services/llm.py` -- `LLMService` class (no constructor dependencies -- no DB access, stateless)
  - [x] 3.2 Implement `async test_connectivity(base_url: str, api_key: str, model_id: str) -> None` -- validates inputs, makes HTTP test request
  - [x] 3.3 Normalize `base_url` (strip trailing slash, ensure not empty)
  - [x] 3.4 Make `GET {base_url}/models` with `Authorization: Bearer {api_key}` header using `httpx.AsyncClient` with 10-second timeout (changed from `/v1/models` to `/models` — base_url now expected to include `/v1`, matching OpenAI SDK convention)
  - [x] 3.5 Raise `LLMConfigError("llm_connection_failed")` on `httpx.ConnectError`/`httpx.RequestError`, `LLMConfigError("llm_auth_failed")` on HTTP 401/403, `LLMConfigError("llm_timeout")` on `httpx.TimeoutException`

- [x] Task 4: Create LLM config session helpers (AC: #4, #5)
  - [x] 4.1 Add helper functions in `easyorario/services/llm.py`: `get_llm_config(session: dict) -> dict | None` and `set_llm_config(request: Request, base_url: str, api_key: str, model_id: str) -> None`
  - [x] 4.2 `get_llm_config` returns `{"base_url": ..., "api_key": ..., "model_id": ...}` or `None` if any key missing
  - [x] 4.3 `set_llm_config` reads current session, merges LLM keys, calls `request.set_session()` with merged dict (CRITICAL: must not overwrite auth session data)
  - [x] 4.4 Create `requires_llm_config` guard function in `easyorario/guards/auth.py` -- reads session, if no LLM config present, raises `NotAuthorizedException` (which the exception handler will handle). Note: actual redirect-to-settings logic will be refined in Story 3.2; for now, the guard just blocks access.

- [x] Task 5: Create SettingsController (AC: #1, #2, #3, #5, #6, #7, #8)
  - [x] 5.1 Create `easyorario/controllers/settings.py` with `path="/impostazioni"`
  - [x] 5.2 `GET /` -- render settings form. If LLM config exists in session, pre-populate `base_url` and `model_id` (NEVER show `api_key`). Guard: `requires_responsible_professor`.
  - [x] 5.3 `POST /` -- parse form data (base_url, api_key, model_id), validate non-empty required fields. If validation fails, re-render with Italian error and submitted values. If valid, call `LLMService.test_connectivity()`. On success: store config in session via `set_llm_config()`, re-render with Italian success message. On `LLMConfigError`: re-render with Italian error and submitted values (except api_key).
  - [x] 5.4 Guard: `requires_responsible_professor` on both GET and POST

- [x] Task 6: Create settings template (AC: #1, #5)
  - [x] 6.1 Create `templates/pages/settings.html` extending `base.html`
  - [x] 6.2 Form fields: base_url (text input, placeholder "https://api.openai.com/v1"), api_key (password input, placeholder "sk-..."), model_id (text input, placeholder "gpt-4o")
  - [x] 6.3 All labels, placeholders, and messages in Italian
  - [x] 6.4 CSRF token included, Oat UI form styling
  - [x] 6.5 Success/error messages via `<div role="alert">`
  - [x] 6.6 Show "Configurazione attiva" badge when config already exists in session

- [x] Task 7: Update navigation and app wiring (AC: #1)
  - [x] 7.1 Add "Impostazioni" link in `templates/base.html` nav -- visible only for authenticated Responsible Professors (check `user.role == "responsible_professor"`)
  - [x] 7.2 Add `provide_llm_service` DI function in `app.py`
  - [x] 7.3 Register `SettingsController` in `route_handlers` list
  - [x] 7.4 Register `provide_llm_service` in `dependencies` dict

- [x] Task 8: Write tests (AC: #1-#8)
  - [x] 8.1 `tests/services/test_llm.py`: test_connectivity with mocked httpx responses (success, 401, 403, connection error, timeout, server error), get_llm_config/set_llm_config helpers, trailing slash normalization
  - [x] 8.2 `tests/controllers/test_settings.py`: GET form renders, POST with valid config (mocked), POST with invalid config (mocked), POST with empty fields, GET as Professor returns 403, GET pre-populates from session, success message after valid POST, reuses api_key when blank, timeout error, preserves values on error

## Dev Notes

### Architecture Patterns & Constraints

- **Layered architecture applies:** SettingsController (HTTP) → LLMService (business logic) → external LLM API. No repository needed — LLM config is session-only, not persisted to DB.
- **`services/llm.py` is the sole LLM API contact point:** Per architecture, ALL external LLM communication goes through this service. Story 3.1 creates the service with connectivity testing; Story 3.2 will add the translation pipeline to the same service.
- **LLM API keys NOT persisted:** Architecture decision — keys are provided per session, stored in HTTP session data only. No encryption needed because there is no data at rest.
- **Guards enforce authorization declaratively:** `requires_responsible_professor` on all settings routes. Only RPs configure LLM endpoints.
- **Session-based config:** LLM configuration (base_url, api_key, model_id) stored alongside auth data in the same session dict. Must MERGE, never replace.

### Session Storage Pattern — CRITICAL

The existing auth login flow uses `request.set_session()` which **replaces** the entire session dict:

```python
# In auth controller (login):
request.clear_session()
request.set_session({"user_id": str(user.id), "email": user.email, "role": user.role})
```

When storing LLM config, you MUST preserve the auth keys. Pattern:

```python
def set_llm_config(request: Request, base_url: str, api_key: str, model_id: str) -> None:
    """Store LLM configuration in session alongside existing auth data."""
    session_data = dict(request.session)  # copy current session (has user_id, email, role)
    session_data["llm_base_url"] = base_url
    session_data["llm_api_key"] = api_key
    session_data["llm_model_id"] = model_id
    request.set_session(session_data)
```

Reading LLM config:

```python
def get_llm_config(session: dict[str, Any]) -> dict[str, str] | None:
    """Extract LLM configuration from session. Returns None if not configured."""
    base_url = session.get("llm_base_url")
    api_key = session.get("llm_api_key")
    model_id = session.get("llm_model_id")
    if not base_url or not api_key:
        return None
    return {"base_url": base_url, "api_key": api_key, "model_id": model_id or ""}
```

**Pitfall:** `request.clear_session()` in the logout handler already wipes everything including LLM config. This is correct — on logout, the user must reconfigure. No changes needed to the logout flow.

### LLM Connectivity Test Design

**Endpoint:** `GET {base_url}/v1/models` — standard OpenAI-compatible endpoint for listing available models. Validates both URL reachability and API key validity without consuming tokens.

**Implementation:**

```python
async def test_connectivity(self, base_url: str, api_key: str, model_id: str) -> None:
    """Test LLM endpoint connectivity. Raises LLMConfigError on failure."""
    url = f"{base_url.rstrip('/')}/v1/models"
    headers = {"Authorization": f"Bearer {api_key}"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(url, headers=headers)
        except httpx.TimeoutException:
            raise LLMConfigError("llm_timeout")
        except httpx.RequestError:
            raise LLMConfigError("llm_connection_failed")
    if response.status_code in (401, 403):
        raise LLMConfigError("llm_auth_failed")
    if response.status_code >= 400:
        raise LLMConfigError("llm_connection_failed")
```

**Design notes:**
- `model_id` is NOT validated against the models list response — this avoids complexity for the PoC. Invalid model IDs will surface as errors in Story 3.2 when actual completions are attempted.
- The 10-second timeout matches NFR-3 (LLM translation latency P95 ≤ 10s). A connectivity test should complete much faster.
- `httpx.RequestError` catches DNS failures, connection refused, SSL errors, etc.

### Controller Form Pattern

**SettingsController follows the existing form pattern from AuthController and TimetableController:**

```python
class SettingsController(Controller):
    path = "/impostazioni"

    @get("/", guards=[requires_responsible_professor])
    async def show_settings(self, request: Request) -> Template:
        llm_config = get_llm_config(request.session)
        return Template(
            template_name="pages/settings.html",
            context={
                "user": request.user,
                "base_url": llm_config["base_url"] if llm_config else "",
                "model_id": llm_config["model_id"] if llm_config else "",
                "has_config": llm_config is not None,
            },
        )

    @post("/", guards=[requires_responsible_professor])
    async def save_settings(
        self,
        request: Request,
        data: Annotated[dict[str, str], Body(media_type=RequestEncodingType.URL_ENCODED)],
        llm_service: LLMService,
    ) -> Template:
        base_url = data.get("base_url", "").strip()
        api_key = data.get("api_key", "").strip()
        model_id = data.get("model_id", "").strip()

        # Validate required fields
        if not base_url:
            return Template(..., context={"error": MESSAGES["llm_base_url_required"], ...})
        if not api_key:
            # If config exists and user left api_key empty, keep existing key
            existing = get_llm_config(request.session)
            if existing:
                api_key = existing["api_key"]
            else:
                return Template(..., context={"error": MESSAGES["llm_api_key_required"], ...})

        # Test connectivity
        try:
            await llm_service.test_connectivity(base_url, api_key, model_id)
        except LLMConfigError as exc:
            return Template(..., context={"error": MESSAGES[exc.error_key], ...})

        # Store in session
        set_llm_config(request, base_url, api_key, model_id)
        return Template(..., context={"success": MESSAGES["llm_config_saved"], ...})
```

**Important detail:** When the user already has a config and revisits the form, the API key is NOT pre-populated (security). If the user submits the form with an empty API key field, we **reuse the existing API key from session** rather than requiring re-entry. This matches AC #5.

### Architecture Compliance

**Boundary Rules — MUST follow:**

| Rule | This Story's Application |
|---|---|
| Controller → Service → Repository (one-way) | SettingsController calls LLMService. No repository layer — LLM config is session-only. |
| `services/llm.py` is the SOLE LLM API contact point | All external HTTP requests to LLM endpoints go through LLMService. Controller NEVER calls httpx directly. |
| LLM API keys NOT persisted to DB | Config stored in HTTP session only. No model, no migration, no DB column for API keys. |
| Controllers handle HTTP only — no business logic | Controller parses form data, passes raw strings to LLMService. Service validates and makes the test request. |
| Guards enforce authorization declaratively | `requires_responsible_professor` guard on both GET and POST `/impostazioni`. |
| Italian user-facing text, English code/logs | Template text in Italian. Python identifiers, comments, log messages in English. |
| `structlog` for all logging, never `print()` | Log config events: `_log.ainfo("llm_config_saved", base_url=base_url)` — NEVER log `api_key`. |
| Use Litestar DI, never manual instantiation | LLMService provided via Litestar's `Provide` / type-hint DI. |
| `snake_case` for Python/JSON, `kebab-case` for URLs | URL: `/impostazioni`. Session keys: `llm_base_url`, `llm_api_key`, `llm_model_id`. |
| `jj` for VCS, never raw `git` | All commits via `jj commit -m "message"`. |

**Anti-Patterns — NEVER do:**

- Do NOT persist LLM API keys to the database — session-only per architecture decision
- Do NOT log the API key in any log message — use `structlog` and explicitly exclude `api_key` from logged fields
- Do NOT hardcode Italian strings in Python code — use templates or `i18n/errors.py` message mappings
- Do NOT make HTTP requests to LLM APIs outside of `services/llm.py` — controller must call the service
- Do NOT use `request.set_session()` without first reading current session — this would overwrite auth data
- Do NOT show the stored API key in the form when pre-populating — security risk
- Do NOT implement constraint translation in this story — that is Story 3.2
- Do NOT create any database models or migrations — this story has no persistence
- Do NOT use bare `except:` or catch `Exception` without re-raising
- Do NOT use `git` commands — use `jj` exclusively
- Do NOT add `from __future__ import annotations`

### Library & Framework Requirements

**httpx (>=0.28.0) — Async HTTP client for LLM connectivity test:**

| API | Usage | Import |
|---|---|---|
| `httpx.AsyncClient` | Async HTTP client context manager | `import httpx` |
| `client.get(url, headers=...)` | Make GET request to LLM endpoint | Method on client |
| `httpx.TimeoutException` | Catch request timeout (>10s) | `import httpx` |
| `httpx.ConnectError` | Catch DNS failure, connection refused | `import httpx` |
| `httpx.RequestError` | Base class for all request errors | `import httpx` |

**httpx usage pattern:**

```python
async with httpx.AsyncClient(timeout=10.0) as client:
    response = await client.get(url, headers=headers)
```

The `timeout=10.0` parameter sets a 10-second timeout for the entire request (connect + read). `AsyncClient` as context manager ensures proper connection cleanup.

**Litestar (>=2.21.0) — Key APIs for this story:**

| API | Usage | Import |
|---|---|---|
| `Request.session` | Read current session dict (contains auth + LLM config) | `from litestar import Request` |
| `Request.set_session()` | Replace session dict (must merge, not overwrite) | `from litestar import Request` |
| `Template` | Render Jinja2 template response | `from litestar.response import Template` |
| `Controller` | Base class for route controllers | `from litestar import Controller` |
| `get`, `post` | Route decorators | `from litestar import get, post` |
| `Body` | Parse form-encoded POST data | `from litestar.params import Body` |
| `RequestEncodingType` | Specify URL-encoded form | `from litestar.enums import RequestEncodingType` |
| `Provide` | DI provider registration | `from litestar.di import Provide` |
| `guards` | Route-level guard list | Route decorator param |

**Litestar session access:**

```python
# Reading session (returns dict[str, Any]):
session_data = request.session  # {"user_id": "...", "email": "...", "role": "...", ...}

# Writing session (MUST merge with existing):
merged = dict(request.session)
merged["llm_base_url"] = base_url
request.set_session(merged)
```

**Litestar form data — dataclass vs dict:**

The existing pattern uses both dataclasses (AuthController) and dicts (TimetableController) for form parsing. For SettingsController, use a dataclass for cleaner typing:

```python
from dataclasses import dataclass

@dataclass
class LLMConfigFormData:
    base_url: str = ""
    api_key: str = ""
    model_id: str = ""
```

Note: `model_id` defaults to empty string since it's optional (user may leave it blank if the provider has a default model).

**Oat UI — Form elements used:**

| Element | HTML | Usage |
|---|---|---|
| Text input | `<input type="text">` | base_url, model_id |
| Password input | `<input type="password">` | api_key (masked) |
| Button | `<button type="submit">` | "Salva configurazione" submit |
| Alert (success) | `<div role="alert">` | Success message after valid config |
| Alert (error) | `<div role="alert">` | Error messages for validation/connectivity |
| Badge | `<span badge>` | "Configurazione attiva" when config exists |
| Form | `<form method="post">` | Standard HTML form with CSRF |

**No new dependencies beyond httpx.** Everything else is already in `pyproject.toml`.

### File Structure Requirements

**Files to CREATE:**

```
easyorario/services/llm.py                        (CREATE: LLMService + session helpers get_llm_config/set_llm_config)
easyorario/controllers/settings.py                 (CREATE: SettingsController at /impostazioni)
templates/pages/settings.html                      (CREATE: LLM config form)
tests/services/test_llm.py                         (CREATE: LLM service tests with mocked httpx)
tests/controllers/test_settings.py                 (CREATE: settings controller integration tests)
```

**Files to UPDATE:**

```
pyproject.toml                                     (UPDATE: add httpx>=0.28.0 to dependencies)
easyorario/exceptions.py                           (UPDATE: add LLMConfigError)
easyorario/i18n/errors.py                          (UPDATE: add LLM config Italian messages)
easyorario/guards/auth.py                          (UPDATE: add requires_llm_config guard)
easyorario/app.py                                  (UPDATE: import SettingsController, add to route_handlers; add provide_llm_service DI)
templates/base.html                                (UPDATE: add "Impostazioni" nav link for RP users)
```

**Files NOT to touch:**

```
easyorario/models/*                                (NO CHANGE — no new models or migrations)
easyorario/repositories/*                          (NO CHANGE — no data persistence)
easyorario/services/auth.py                        (NO CHANGE)
easyorario/services/timetable.py                   (NO CHANGE)
easyorario/controllers/auth.py                     (NO CHANGE)
easyorario/controllers/timetable.py                (NO CHANGE — vincoli stub may still exist if Story 2.2 hasn't run yet; do NOT remove it here)
easyorario/controllers/dashboard.py                (NO CHANGE)
easyorario/config.py                               (NO CHANGE — no new env vars needed; LLM config is user-provided per session)
alembic/                                           (NO CHANGE — no migrations)
templates/pages/dashboard.html                     (NO CHANGE)
templates/pages/timetable_new.html                 (NO CHANGE)
templates/pages/timetable_constraints.html         (NO CHANGE)
```

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
- `authenticated_client` — logged-in Responsible Professor
- `authenticated_professor_client` — logged-in Professor
- `_get_csrf_token()` helper

New fixture needed for mocking httpx:
```python
@pytest.fixture
def mock_llm_success(monkeypatch):
    """Mock httpx to return a successful /v1/models response."""
    import httpx

    async def mock_get(self, url, **kwargs):
        return httpx.Response(200, json={"data": [{"id": "gpt-4o"}]})

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)
```

**Required Test Cases:**

| Test File | Test Name | Verifies |
|---|---|---|
| `test_llm.py` (service) | `test_connectivity_with_reachable_endpoint_succeeds` | Happy path with mocked 200 response |
| `test_llm.py` (service) | `test_connectivity_with_unreachable_url_raises` | `LLMConfigError("llm_connection_failed")` on ConnectError |
| `test_llm.py` (service) | `test_connectivity_with_bad_api_key_raises` | `LLMConfigError("llm_auth_failed")` on 401 response |
| `test_llm.py` (service) | `test_connectivity_with_timeout_raises` | `LLMConfigError("llm_timeout")` on TimeoutException |
| `test_llm.py` (service) | `test_connectivity_with_server_error_raises` | `LLMConfigError("llm_connection_failed")` on 500 response |
| `test_llm.py` (helpers) | `test_get_llm_config_returns_none_when_not_set` | No config in session → None |
| `test_llm.py` (helpers) | `test_get_llm_config_returns_dict_when_set` | Config present → dict with base_url, api_key, model_id |
| `test_settings.py` (controller) | `test_get_impostazioni_renders_form` | AC #1: form with correct fields |
| `test_settings.py` (controller) | `test_get_impostazioni_as_professor_returns_403` | AC #6: role guard blocks |
| `test_settings.py` (controller) | `test_post_impostazioni_with_valid_config_shows_success` | AC #2: success message (mocked httpx) |
| `test_settings.py` (controller) | `test_post_impostazioni_stores_config_in_session` | AC #2: session contains LLM keys after POST |
| `test_settings.py` (controller) | `test_post_impostazioni_with_unreachable_url_shows_error` | AC #3: Italian error message |
| `test_settings.py` (controller) | `test_post_impostazioni_with_empty_base_url_shows_error` | AC #7: validation error |
| `test_settings.py` (controller) | `test_post_impostazioni_with_empty_api_key_shows_error` | AC #7: validation error |
| `test_settings.py` (controller) | `test_get_impostazioni_prepopulates_from_session` | AC #5: base_url and model_id shown, api_key NOT shown |
| `test_settings.py` (controller) | `test_post_impostazioni_reuses_api_key_when_blank` | AC #5: existing api_key reused if field left empty |
| `test_settings.py` (controller) | `test_post_impostazioni_with_timeout_shows_error` | AC #8: timeout error message |

**Mocking strategy for httpx in controller tests:**

Controller tests go through the full Litestar request cycle (AsyncTestClient). The LLM test request is an external HTTP call that must be mocked. Use `monkeypatch` to patch `httpx.AsyncClient.get` at the module level, or better, mock `LLMService.test_connectivity` directly since controller tests shouldn't re-test service logic:

```python
async def test_post_impostazioni_with_valid_config_shows_success(
    authenticated_client, monkeypatch,
):
    """POST with valid config stores in session and shows success."""
    # Mock the LLM service to succeed
    async def mock_test_connectivity(self, base_url, api_key, model_id):
        return None  # success = no exception

    monkeypatch.setattr(
        "easyorario.services.llm.LLMService.test_connectivity",
        mock_test_connectivity,
    )

    csrf = _get_csrf_token(authenticated_client)
    response = await authenticated_client.post(
        "/impostazioni",
        data={
            "base_url": "https://api.openai.com",
            "api_key": "sk-test-key",
            "model_id": "gpt-4o",
        },
        headers={"x-csrftoken": csrf},
    )
    assert response.status_code == 200
    assert "successo" in response.text.lower()
```

**In-memory session pattern:**

The test client's `MemoryStore` session backend persists across requests within the same test function. After a successful POST to `/impostazioni`, a subsequent GET should show the pre-populated form. Test this by making two requests in the same test:

```python
async def test_get_impostazioni_prepopulates_from_session(authenticated_client, monkeypatch):
    # First: POST valid config
    ...mock and post...
    # Then: GET should show pre-populated values
    response = await authenticated_client.get("/impostazioni")
    assert "https://api.openai.com" in response.text
    assert "gpt-4o" in response.text
    assert "sk-test-key" not in response.text  # API key NEVER shown
```

### Previous Story Intelligence

**From Story 2.1 (Create New Timetable) — Most recent completed story:**

- **Controller pattern established:** Dataclass for form data parsing, `Body(media_type=RequestEncodingType.URL_ENCODED)`, try/except on domain exceptions with `MESSAGES[exc.error_key]` for error rendering, `context={"user": request.user, "form": data}` for re-populating form on error.
- **DI pattern:** `provide_timetable_service(timetable_repo)` → registered in `app.py` dependencies dict. Follow same for `provide_llm_service()`.
- **Guard pattern:** `guards=[requires_responsible_professor]` on route decorators. Works for both GET and POST.
- **CSRF pattern:** All POST forms include `{{ csrf_input | safe }}`. Tests use `_get_csrf_token(client)` + `headers={"x-csrftoken": csrf}`.
- **Template pattern:** `{% extends "base.html" %}`, `{% block title %}`, `{% block content %}`. Error displayed via `{% if error %}<div role="alert">{{ error }}</div>{% endif %}`.
- **autocommit on redirect is configured** — but this story doesn't redirect after POST (it re-renders the template with success/error). The POST returns a Template, not a Redirect.
- **Session-cached user auth:** `retrieve_user_handler` reconstructs User from session keys (`user_id`, `email`, `role`). LLM config keys will coexist in the same session dict.

**From Story 2.1 dev notes — key learnings:**
- `request.user` raises `KeyError` not `AttributeError` when user not in scope — use `request.scope.get("user")` in exception handlers.
- Service accepts raw strings, does all validation, raises domain exceptions with error_key.
- Controller catches domain exceptions, re-renders template with error message from `MESSAGES`.

**From Story 2.2 (Constraint Input) — adjacent story (ready-for-dev, not yet implemented):**
- Story 2.2 creates the ConstraintController at `/orario/{id}/vincoli`. It removes the vincoli stub from TimetableController. If 2.2 has NOT been implemented when 3.1 starts, the stub still exists in TimetableController — do NOT touch it.
- Story 2.2 establishes the ownership verification pattern (check `timetable.owner_id == request.user.id`). Not relevant for 3.1 since settings is user-scoped, not timetable-scoped.

### Git Intelligence

**Recent commits (Story 2.1):**
```
5cf39fc story 2.1: code review fixes — missing tests, error key, file list
9a4fb4b story 2.1: finalize — update story and sprint status to review
e17101a story 2.1: controller, templates, DI wiring, session-cached user auth (tasks 5-7)
caf6b44 story 2.1: timetable service with validation, domain exceptions, i18n messages (tasks 3-4)
c1ad674 story 2.1: timetable repository with get_by_owner (task 2)
a43640e story 2.1: timetable model, user relationship, and alembic migration (task 1)
```

**Commit patterns to follow:**
- Atomic commits per task group: `story 3.1: description (task N)`
- `just check` before every commit (format + lint + typecheck)
- `just test` separately to verify tests pass
- structlog for all logging with descriptive event names
- Top-level imports preferred over lazy imports

**Suggested commit sequence for Story 3.1:**
1. `story 3.1: add httpx dependency, LLM exceptions, i18n messages (tasks 1-2)`
2. `story 3.1: LLM service with connectivity test and session helpers (tasks 3-4)`
3. `story 3.1: settings controller, template, nav link, DI wiring (tasks 5-7)`
4. `story 3.1: comprehensive tests for LLM service and settings controller (task 8)`

### Project Structure Notes

- **Flat layout confirmed:** `easyorario/` at project root (no `src/`). The architecture doc mentions `src/easyorario/` but the actual project uses `easyorario/` directly. Follow what exists, not the architecture doc.
- **Tests at `tests/`** at project root, mirroring `easyorario/` structure.
- **Templates at `templates/`** at project root.
- **Static at `static/`** at project root.
- **Nav in `templates/base.html`** — simple inline layout with conditional user/login links. The "Impostazioni" link goes here, guarded by `{% if user and user.role == "responsible_professor" %}`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.1]
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 3 overview]
- [Source: _bmad-output/planning-artifacts/architecture.md#Authentication & Security — LLM API keys not stored]
- [Source: _bmad-output/planning-artifacts/architecture.md#Core Architectural Decisions — LLM integration boundary]
- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure & Boundaries — services/llm.py]
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns & Consistency Rules]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Site Map — /impostazioni]
- [Source: _bmad-output/implementation-artifacts/2-1-create-new-timetable.md — controller/DI/session patterns]
- [Source: easyorario/app.py — DI registration, session auth, retrieve_user_handler]
- [Source: easyorario/controllers/auth.py — session set/clear pattern]
- [Source: easyorario/guards/auth.py — requires_responsible_professor]
- [Source: easyorario/exceptions.py — domain exception pattern]
- [Source: easyorario/i18n/errors.py — Italian message mappings]
- [Source: templates/base.html — nav layout]
- [Source: CLAUDE.md#Architecture]
- [Source: CLAUDE.md#Commands]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

No blocking issues encountered during implementation.

### Completion Notes List

- Implemented LLMService with connectivity test via `GET {base_url}/models` (OpenAI-compatible). Changed from story spec's `/v1/models` to just `/models` since base_url now includes `/v1` per current OpenAI SDK convention.
- LLM config stored in HTTP session alongside auth data using merge pattern (never overwrites auth keys).
- `requires_llm_config` guard created for future use in Story 3.2 (constraint translation).
- SettingsController at `/impostazioni` with full form flow: validation, connectivity test, session storage, pre-population, api_key reuse.
- Template uses Oat UI semantic HTML (data-field, data-hint, role="alert", badge).
- All Italian user-facing messages via i18n/errors.py MESSAGES dict — no hardcoded strings in Python.
- 17 service tests + 12 controller tests = 29 new tests. Full suite: 128 tests, 0 failures.
- `just check` passes (format + lint + typecheck).

### File List

**Created:**
- `easyorario/services/llm.py` — LLMService with test_connectivity, get_llm_config, set_llm_config
- `easyorario/controllers/settings.py` — SettingsController at /impostazioni
- `templates/pages/settings.html` — LLM configuration form (Oat UI)
- `tests/services/test_llm.py` — 17 tests for LLM service, helpers, and requires_llm_config guard
- `tests/controllers/test_settings.py` — 12 tests for settings controller

**Modified:**
- `pyproject.toml` — added httpx>=0.28.0 dependency
- `easyorario/exceptions.py` — added LLMConfigError
- `easyorario/i18n/errors.py` — added 7 LLM-related Italian messages
- `easyorario/guards/auth.py` — added requires_llm_config guard
- `easyorario/app.py` — imported SettingsController, LLMService; added provide_llm_service DI; registered SettingsController
- `templates/base.html` — added "Impostazioni" nav link for RP users

## Change Log

- 2026-02-18: Story 3.1 implemented — LLM endpoint configuration with connectivity test, session-based config storage, settings form at /impostazioni, role-based access control, and comprehensive test coverage (25 tests).
- 2026-02-18: Code review fixes — removed unused structlog import from llm.py, added 3 guard tests for requires_llm_config, added POST-as-professor 403 test, added HTML required attributes on form inputs. Test count: 29 new tests, 128 total.
