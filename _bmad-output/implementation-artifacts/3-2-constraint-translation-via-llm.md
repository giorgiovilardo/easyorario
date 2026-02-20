# Story 3.2: Constraint Translation via LLM

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->
<!-- Prerequisites: Story 2.2 (Constraint Input) and Story 3.1 (LLM Endpoint Configuration) MUST be completed before starting this story. -->

## Story

As a Responsible Professor,
I want the system to translate my Italian constraints into formal representations,
so that they can be used by the constraint solver.

## Acceptance Criteria

1. **Given** I have pending constraints and a configured LLM endpoint **When** I click "Verifica vincoli" on `/orario/{id}/vincoli` **Then** each pending constraint is sent to the LLM for translation and I am redirected to `/orario/{id}/vincoli/verifica`

2. **Given** the LLM processes a constraint **When** translation completes successfully **Then** the constraint's `formal_representation` (JSON) is stored in the database and its status changes from `"pending"` to `"translated"`

3. **Given** the LLM is unavailable or returns an error **When** translation fails for a constraint **Then** I see an Italian error message on the verification page and can retry translation or go back to rephrase the constraint

4. **Given** the LLM returns a malformed or unparseable constraint representation **When** JSON schema validation rejects it **Then** the constraint's status changes to `"translation_failed"` and I see an Italian message asking me to rephrase the constraint

5. **Given** performance requirements (NFR-3) **When** a constraint is translated **Then** the translation completes within 10 seconds (P95) per constraint

6. **Given** I have no LLM endpoint configured in my session **When** I click "Verifica vincoli" **Then** I am redirected to `/impostazioni` with an Italian flash message ("Configura l'endpoint LLM prima di procedere")

7. **Given** I have no pending constraints (all already translated or verified) **When** I click "Verifica vincoli" **Then** I am taken directly to the verification page showing already-translated constraints

8. **Given** I am on the verification page `/orario/{id}/vincoli/verifica` **When** I view the page **Then** I see a card for each translated constraint showing: original Italian text, structured human-readable interpretation, and a collapsible `<details>` section with the formal JSON representation. Constraints that failed translation show an error badge and a "Riprova" (retry) button.

## Tasks / Subtasks

- [ ] Task 1: Add pydantic dependency, LLM translation exception, and Italian messages (AC: #3, #4)
  - [ ] 1.1 Add `pydantic>=2.0` to `pyproject.toml` dependencies and run `uv sync`
  - [ ] 1.2 Add `LLMTranslationError` exception class to `easyorario/exceptions.py` (same pattern as `LLMConfigError` — accepts `error_key`)
  - [ ] 1.3 Add Italian messages to `easyorario/i18n/errors.py`: `llm_translation_failed` ("Errore durante la traduzione del vincolo"), `llm_translation_malformed` ("Il modello ha restituito una risposta non valida. Prova a riformulare il vincolo"), `llm_translation_timeout` ("Timeout durante la traduzione del vincolo"), `translation_success` ("Vincoli tradotti con successo"), `all_translations_failed` ("Impossibile tradurre i vincoli. Verifica la configurazione LLM o riformula i vincoli"), `no_pending_constraints` ("Nessun vincolo in attesa di traduzione")

- [ ] Task 2: Define constraint schema model and add `translate_constraint` to LLMService (AC: #1, #2, #3, #4, #5)
  - [ ] 2.1 Create Pydantic model `ConstraintTranslation` in `easyorario/services/llm.py` defining the formal constraint representation (see Dev Notes for full model definition). Use `model_config = ConfigDict(extra="forbid")` for OpenAI strict mode compatibility (`additionalProperties: false`). All fields required (nullable fields use `str | None` without defaults)
  - [ ] 2.2 Create module-level constant `CONSTRAINT_RESPONSE_FORMAT` dict built from `ConstraintTranslation.model_json_schema()` wrapped in the OpenAI structured outputs envelope: `{"type": "json_schema", "json_schema": {"name": "constraint_translation", "strict": True, "schema": <model_json_schema output>}}`
  - [ ] 2.3 Create the system prompt template for Italian constraint translation (must include timetable context: subjects, teachers, weekly_hours, class_identifier). Store as module-level constant `TRANSLATION_SYSTEM_PROMPT`
  - [ ] 2.4 Implement `async translate_constraint(self, *, base_url: str, api_key: str, model_id: str, constraint_text: str, timetable_context: dict) -> dict` — calls `POST {base_url}/chat/completions` with `response_format=CONSTRAINT_RESPONSE_FORMAT`, system prompt with timetable context, and user message with constraint text
  - [ ] 2.5 Parse `response.json()["choices"][0]["message"]["content"]` via `ConstraintTranslation.model_validate_json(content)` — Pydantic validates the response against the schema and returns a typed object. Call `.model_dump()` to get the dict for storage in `formal_representation`
  - [ ] 2.6 Raise `LLMTranslationError("llm_translation_failed")` on `httpx.RequestError`/`httpx.TimeoutException`, `LLMTranslationError("llm_translation_malformed")` on `json.JSONDecodeError` or `pydantic.ValidationError`, `LLMConfigError("llm_auth_failed")` on HTTP 401/403

- [ ] Task 3: Add `translate_pending_constraints` method to ConstraintService (AC: #1, #2, #3, #4, #7)
  - [ ] 3.1 Add `LLMService` as a constructor dependency: `__init__(self, constraint_repo, llm_service)`
  - [ ] 3.2 Implement `async translate_pending_constraints(self, *, timetable: Timetable, llm_config: dict[str, str]) -> list[Constraint]` — fetches pending constraints, translates each via LLMService, updates status and formal_representation
  - [ ] 3.3 For each pending constraint: call `llm_service.translate_constraint()`, on success set `status="translated"` and `formal_representation=result`, on `LLMTranslationError` set `status="translation_failed"` and `formal_representation=None`
  - [ ] 3.4 Build timetable_context dict from Timetable object: `{"class_identifier": ..., "weekly_hours": ..., "subjects": ..., "teachers": ...}`
  - [ ] 3.5 Update each constraint in the repository after translation attempt
  - [ ] 3.6 Return the full list of constraints (translated + failed + already-translated from previous runs)

- [ ] Task 4: Update ConstraintController with verification routes (AC: #1, #6, #7, #8)
  - [ ] 4.1 Add `POST /verifica` route — guards: `requires_responsible_professor`, `requires_llm_config`. Reads LLM config from session, loads timetable (with ownership check), calls `constraint_service.translate_pending_constraints()`, renders verification template
  - [ ] 4.2 Add `GET /verifica` route — guards: `requires_responsible_professor`. Loads timetable + all constraints, renders verification template without re-translating (for revisiting the page)
  - [ ] 4.3 Handle the case where there are no pending constraints on POST: skip translation, render verification page with already-translated constraints
  - [ ] 4.4 Handle `LLMConfigError` (redirect to `/impostazioni` with flash message) — this case is already handled by `requires_llm_config` guard, which raises `NotAuthorizedException`

- [ ] Task 5: Update constraint list template and create verification template (AC: #1, #8)
  - [ ] 5.1 Update `templates/pages/timetable_constraints.html`: change "Verifica vincoli" `<a>` link to a `<form method="post" action="...">` button, add badges for `"translated"` and `"translation_failed"` statuses
  - [ ] 5.2 Create `templates/pages/timetable_verification.html`: extends `base.html`, shows constraint cards with original text, human-readable `description` from formal_representation, collapsible `<details>` with JSON debug output, error badges for failed translations, "Riprova" (retry) button for failed constraints, navigation back to constraint list
  - [ ] 5.3 Show success/error summary at the top (e.g., "3 vincoli tradotti, 1 errore")

- [ ] Task 6: Update app.py DI wiring (AC: all)
  - [ ] 6.1 Update `provide_constraint_service` to accept `llm_service: LLMService` and pass it to the constructor
  - [ ] 6.2 No new controllers to register (ConstraintController already registered, new routes are within it)

- [ ] Task 7: Write tests (AC: #1-#8)
  - [ ] 7.1 `tests/services/test_llm.py` (additions): test translate_constraint happy path (mocked httpx POST), test with malformed JSON response, test with schema validation failure, test with timeout, test with connection error, test with auth failure (401), test system prompt includes timetable context
  - [ ] 7.2 `tests/services/test_constraint.py` (additions): test translate_pending_constraints translates all pending, test partial failure (some succeed some fail), test no pending constraints returns existing, test status updates correctly, test formal_representation stored on success and None on failure
  - [ ] 7.3 `tests/controllers/test_constraint.py` (additions): test POST /verifica translates and renders page, test POST /verifica as Professor returns 403, test POST /verifica without LLM config redirects, test GET /verifica shows already-translated constraints, test POST /verifica for non-owned timetable returns 403, test POST /verifica with no pending constraints shows existing, test verification page shows constraint cards with correct content

## Dev Notes

### LLM Translation Design — Core Architecture

**This is the first story that makes actual LLM API calls for constraint translation.** Story 3.1 only tested connectivity (`GET /models`). Story 3.2 implements the real translation pipeline (`POST /chat/completions`).

**Flow:**
1. User clicks "Verifica vincoli" (POST form button on constraint list page)
2. POST `/orario/{id}/vincoli/verifica` → ConstraintController
3. Controller checks ownership, checks LLM config in session (redirects to `/impostazioni` if missing)
4. Controller calls `constraint_service.translate_pending_constraints(timetable, llm_config)`
5. ConstraintService iterates pending constraints, for each calls `llm_service.translate_constraint()`
6. LLMService builds system prompt with timetable context, calls `POST {base_url}/chat/completions` with Structured Outputs
7. Response parsed via `ConstraintTranslation.model_validate_json()` → stored in `formal_representation`
8. Constraint status updated to `"translated"` (success) or `"translation_failed"` (failure)
9. Controller renders verification template with all constraints

**Revisiting:** GET `/orario/{id}/vincoli/verifica` shows already-translated constraints without re-translating.

### Pydantic Model for Structured Outputs

Define `ConstraintTranslation` in `easyorario/services/llm.py`:

```python
from pydantic import BaseModel, ConfigDict

class ConstraintTranslation(BaseModel):
    """Formal representation of a translated scheduling constraint."""
    model_config = ConfigDict(extra="forbid")

    constraint_type: str
    description: str
    teacher: str | None
    subject: str | None
    days: list[str] | None
    time_slots: list[int] | None
    max_consecutive_hours: int | None
    room: str | None
    notes: str | None
```

**Why this shape:**
- `constraint_type`: one of `teacher_unavailable`, `teacher_preferred`, `subject_scheduling`, `max_consecutive`, `room_requirement`, `general` — tells the Z3 solver (Story 4.1) how to model the constraint
- `description`: human-readable Italian rephrase — shown on the verification card (the "interpretation")
- Remaining fields: nullable, filled based on `constraint_type`. The LLM fills relevant ones and sets others to `null`
- `ConfigDict(extra="forbid")` → `additionalProperties: false` in JSON schema (required by OpenAI strict mode)
- All fields required (no defaults) → all appear in `required` array (required by OpenAI strict mode)
- Nullable via `str | None` → generates `{"anyOf": [{"type": "string"}, {"type": "null"}]}` in schema

**Build the response format constant:**

```python
CONSTRAINT_RESPONSE_FORMAT: dict = {
    "type": "json_schema",
    "json_schema": {
        "name": "constraint_translation",
        "strict": True,
        "schema": ConstraintTranslation.model_json_schema(),
    },
}
```

**Parse LLM response:**

```python
content = response_data["choices"][0]["message"]["content"]
result = ConstraintTranslation.model_validate_json(content)
return result.model_dump()
```

`model_validate_json()` handles JSON parsing AND Pydantic validation in one step. On failure, raises `pydantic.ValidationError`. `model_dump()` returns a plain dict suitable for storing in the JSON `formal_representation` column.

### System Prompt Design

Store as `TRANSLATION_SYSTEM_PROMPT` template string in `easyorario/services/llm.py`. The prompt is formatted at runtime with timetable context:

```python
TRANSLATION_SYSTEM_PROMPT = """\
Sei un traduttore di vincoli per orari scolastici italiani. Dato un vincolo espresso in linguaggio naturale italiano, traducilo in una rappresentazione strutturata JSON.

Contesto dell'orario:
- Classe: {class_identifier}
- Ore settimanali: {weekly_hours}
- Materie: {subjects}
- Docenti: {teachers}
- Giorni: lunedì, martedì, mercoledì, giovedì, venerdì, sabato
- Fasce orarie: da 1 a {max_slots} (1 = prima ora, 2 = seconda ora, ecc.)

Tipi di vincolo (constraint_type):
- teacher_unavailable: un docente non è disponibile in certi giorni/ore
- teacher_preferred: un docente preferisce certi giorni/ore
- subject_scheduling: una materia deve/non deve essere in certi giorni/ore
- max_consecutive: limite massimo di ore consecutive per materia/docente
- room_requirement: una materia richiede una specifica aula/laboratorio
- general: vincolo che non rientra nelle categorie precedenti

Regole:
- Il campo "description" deve essere una riformulazione chiara e precisa del vincolo in italiano
- Compila solo i campi pertinenti al tipo di vincolo, usa null per gli altri
- I nomi dei giorni devono essere in italiano minuscolo
- Le fasce orarie sono numeri interi (1 = prima ora, 2 = seconda ora, ecc.)
- I nomi di docenti e materie devono corrispondere esattamente a quelli forniti nel contesto, se possibile\
"""
```

**User message format:**
```python
f'Traduci questo vincolo: "{constraint_text}"'
```

### LLM API Call Pattern

```python
async def translate_constraint(
    self,
    *,
    base_url: str,
    api_key: str,
    model_id: str,
    constraint_text: str,
    timetable_context: dict,
) -> dict:
    """Translate an Italian NL constraint to formal representation via LLM."""
    system_prompt = TRANSLATION_SYSTEM_PROMPT.format(**timetable_context)
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f'Traduci questo vincolo: "{constraint_text}"'},
        ],
        "response_format": CONSTRAINT_RESPONSE_FORMAT,
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
        except httpx.TimeoutException:
            raise LLMTranslationError("llm_translation_timeout") from None
        except httpx.RequestError:
            raise LLMTranslationError("llm_translation_failed") from None

    if response.status_code in (401, 403):
        raise LLMConfigError("llm_auth_failed")
    if response.status_code >= 400:
        raise LLMTranslationError("llm_translation_failed")

    try:
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        result = ConstraintTranslation.model_validate_json(content)
        return result.model_dump()
    except (KeyError, IndexError, json.JSONDecodeError, ValidationError):
        raise LLMTranslationError("llm_translation_malformed") from None
```

**Key design decisions:**
- **10-second timeout** matches NFR-3 (LLM translation latency P95 ≤ 10s)
- **Structured Outputs** with `response_format` ensures the LLM returns valid JSON matching our schema
- **Pydantic validation** as safety net: `model_validate_json()` catches edge cases where provider doesn't fully enforce the schema
- **`from None`** on raises to suppress exception chains in user-facing errors
- **Auth errors** raise `LLMConfigError` (not `LLMTranslationError`) because the fix is to reconfigure the endpoint

### ConstraintService Translation Orchestration

```python
async def translate_pending_constraints(
    self,
    *,
    timetable: Timetable,
    llm_config: dict[str, str],
) -> list[Constraint]:
    """Translate all pending constraints for a timetable via LLM."""
    constraints = await self.constraint_repo.get_by_timetable(timetable.id)
    pending = [c for c in constraints if c.status == "pending"]

    timetable_context = {
        "class_identifier": timetable.class_identifier,
        "weekly_hours": timetable.weekly_hours,
        "subjects": ", ".join(timetable.subjects),
        "teachers": ", ".join(f"{subj}: {teacher}" for subj, teacher in timetable.teachers.items()),
        "max_slots": timetable.weekly_hours // 6,  # rough: weekly_hours / 6 days
    }

    for constraint in pending:
        try:
            result = await self.llm_service.translate_constraint(
                base_url=llm_config["base_url"],
                api_key=llm_config["api_key"],
                model_id=llm_config["model_id"],
                constraint_text=constraint.natural_language_text,
                timetable_context=timetable_context,
            )
            constraint.formal_representation = result
            constraint.status = "translated"
        except (LLMTranslationError, LLMConfigError) as exc:
            constraint.status = "translation_failed"
            constraint.formal_representation = None
            await _log.awarning(
                "constraint_translation_failed",
                constraint_id=str(constraint.id),
                error_key=exc.error_key,
            )
        await self.constraint_repo.update(constraint)

    # Return ALL constraints (not just pending) so the verification page shows everything
    return await self.constraint_repo.get_by_timetable(timetable.id)
```

**Key design decisions:**
- **Sequential translation** — constraints are translated one at a time. Parallel translation could be added later but adds complexity (rate limiting, error handling). NFR-3 says 10s per constraint; for ~10 constraints that's ~100s worst case, which is acceptable for the PoC
- **Partial failure handling** — each constraint is translated independently. If one fails, others still succeed. The verification page shows both successes and failures
- **Status transitions**: `pending` → `translated` (success) or `pending` → `translation_failed` (failure)
- **Repository `update()`** persists each constraint immediately after translation attempt. Autocommit handler commits the session when the response is sent
- **Returns ALL constraints** — the verification page needs to show everything (translated, failed, and any already-verified from previous runs)
- **`max_slots` calculation** — rough estimate (`weekly_hours / 6 days`). The exact slot count may vary, but this gives the LLM a reasonable range for the system prompt

### Controller Verification Routes

```python
@post("/verifica", guards=[requires_responsible_professor])
async def translate_constraints(
    self,
    request: Request,
    timetable_id: uuid.UUID,
    timetable_repo: TimetableRepository,
    constraint_service: ConstraintService,
) -> Template | Redirect:
    """Trigger LLM translation of pending constraints and render verification page."""
    # Check LLM config (NOT using requires_llm_config guard — we want redirect, not 403)
    llm_config = get_llm_config(request.session)
    if not llm_config:
        return Redirect(path="/impostazioni")

    timetable = await timetable_repo.get(timetable_id)
    if timetable.owner_id != request.user.id:
        raise NotAuthorizedException(detail="Insufficient permissions")

    constraints = await constraint_service.translate_pending_constraints(
        timetable=timetable,
        llm_config=llm_config,
    )

    translated_count = sum(1 for c in constraints if c.status == "translated")
    failed_count = sum(1 for c in constraints if c.status == "translation_failed")

    return Template(
        template_name="pages/timetable_verification.html",
        context={
            "timetable": timetable,
            "constraints": constraints,
            "translated_count": translated_count,
            "failed_count": failed_count,
            "user": request.user,
        },
    )


@get("/verifica", guards=[requires_responsible_professor])
async def show_verification(
    self,
    request: Request,
    timetable_id: uuid.UUID,
    timetable_repo: TimetableRepository,
    constraint_service: ConstraintService,
) -> Template:
    """Show already-translated constraints without re-translating."""
    timetable = await timetable_repo.get(timetable_id)
    if timetable.owner_id != request.user.id:
        raise NotAuthorizedException(detail="Insufficient permissions")

    constraints = await constraint_service.list_constraints(timetable_id=timetable_id)
    translated_count = sum(1 for c in constraints if c.status == "translated")
    failed_count = sum(1 for c in constraints if c.status == "translation_failed")

    return Template(
        template_name="pages/timetable_verification.html",
        context={
            "timetable": timetable,
            "constraints": constraints,
            "translated_count": translated_count,
            "failed_count": failed_count,
            "user": request.user,
        },
    )
```

**Why NOT use `requires_llm_config` guard on POST /verifica:**
The guard raises `NotAuthorizedException` → the exception handler shows 403. But AC #6 requires a redirect to `/impostazioni`. The controller handles this directly with `Redirect(path="/impostazioni")` for better UX. The `requires_llm_config` guard still exists for future use but is NOT applied here.

**GET vs POST /verifica:**
- POST triggers translation, then shows results (side-effect action → POST is correct HTTP method)
- GET shows already-translated constraints (idempotent, safe for bookmarking/refreshing)
- Both routes are on the same path `/verifica` — Litestar disambiguates by HTTP method

### Template: Constraint List Update

Update `templates/pages/timetable_constraints.html`:

1. **Change "Verifica vincoli" link to a POST form button:**
```html
{% if has_pending %}
<form method="post" action="/orario/{{ timetable.id }}/vincoli/verifica">
  {{ csrf_input | safe }}
  <button type="submit" class="w-100 outline">Verifica vincoli</button>
</form>
{% endif %}
```

2. **Add badges for new statuses:**
```html
{% elif constraint.status == "translated" %}
<span badge data-variant="warning">tradotto</span>
{% elif constraint.status == "translation_failed" %}
<span badge data-variant="error">errore traduzione</span>
```

### Template: Verification Page

Create `templates/pages/timetable_verification.html`:

```html
{% extends "base.html" %}
{% block title %}Verifica vincoli — {{ timetable.class_identifier }} — Easyorario{% endblock %}
{% block content %}
<div class="container" style="--container-max: 640px;">
  <h1>Verifica vincoli — {{ timetable.class_identifier }}</h1>

  {% if translated_count or failed_count %}
  <p>
    {% if translated_count %}<span badge data-variant="success">{{ translated_count }} tradotti</span>{% endif %}
    {% if failed_count %}<span badge data-variant="error">{{ failed_count }} errori</span>{% endif %}
  </p>
  {% endif %}

  {% for constraint in constraints %}
  {% if constraint.status in ["translated", "translation_failed", "verified", "rejected"] %}
  <article class="card">
    <p><strong>Vincolo originale:</strong> {{ constraint.natural_language_text }}</p>

    {% if constraint.status == "translated" and constraint.formal_representation %}
    <p>
      <span badge data-variant="warning">tradotto</span>
      <strong>Interpretazione:</strong> {{ constraint.formal_representation.description }}
    </p>
    <details>
      <summary>Dettagli tecnici (JSON)</summary>
      <pre><code>{{ constraint.formal_representation | tojson(indent=2) }}</code></pre>
    </details>
    {% elif constraint.status == "translation_failed" %}
    <p><span badge data-variant="error">errore traduzione</span> Impossibile tradurre il vincolo. Prova a riformularlo.</p>
    {% elif constraint.status == "verified" %}
    <p><span badge data-variant="success">verificato</span> {{ constraint.formal_representation.description }}</p>
    {% elif constraint.status == "rejected" %}
    <p><span badge data-variant="error">rifiutato</span></p>
    {% endif %}
  </article>
  {% endif %}
  {% endfor %}

  <div class="hstack">
    <a href="/orario/{{ timetable.id }}/vincoli" class="button outline">Torna ai vincoli</a>
    <!-- Approve/Reject buttons will be added in Story 3.3 -->
  </div>
</div>
{% endblock %}
```

**Key template decisions:**
- Only shows constraints that have been through translation (not `pending` ones)
- `tojson(indent=2)` Jinja2 filter for pretty-printing the formal_representation JSON in `<details>`
- `constraint.formal_representation.description` accesses the human-readable interpretation from the dict stored in JSON column
- Approve/Reject buttons are NOT included — that's Story 3.3
- Shows `verified` and `rejected` statuses too (forward-compatible with Story 3.3)

### Architecture Compliance

**Boundary Rules — MUST follow:**

| Rule | This Story's Application |
|---|---|
| Controller → Service → Repository (one-way) | ConstraintController calls ConstraintService (which calls LLMService). Controller NEVER calls LLMService directly. |
| `services/llm.py` is the SOLE LLM API contact point | `translate_constraint()` method in LLMService makes the `POST /chat/completions` call. No httpx calls in ConstraintService or controller. |
| LLM API keys NOT persisted to DB | Keys read from session in the controller and passed as `llm_config` dict to the service. No new DB columns for keys. |
| Controllers handle HTTP only — no business logic | Controller reads session, loads timetable, delegates to ConstraintService. Service handles translation orchestration and status updates. |
| Guards enforce authorization declaratively | `requires_responsible_professor` guard on both POST and GET `/verifica`. LLM config check done in controller (NOT via guard) for redirect UX. |
| Italian user-facing text, English code/logs | Template text in Italian. Python identifiers, comments, log messages in English. |
| `structlog` for all logging, never `print()` | Log translation events: `constraint_translated`, `constraint_translation_failed`. NEVER log `api_key`. |
| Use Litestar DI, never manual instantiation | LLMService injected into ConstraintService via DI. Both services provided via `Provide` in app.py. |
| `snake_case` for Python/JSON, `kebab-case` for URLs | URL: `/verifica`. JSON fields: `constraint_type`, `time_slots`, `formal_representation`. |
| `jj` for VCS, never raw `git` | All commits via `jj commit -m "message"`. |

**Anti-Patterns — NEVER do:**

- Do NOT call LLM APIs outside of `services/llm.py` — ConstraintService calls LLMService, never httpx directly
- Do NOT persist LLM API keys to the database — session-only per architecture decision
- Do NOT log the API key in any log message — explicitly exclude from logged fields
- Do NOT hardcode Italian strings in Python code — use templates or `i18n/errors.py` message mappings
- Do NOT use `requires_llm_config` guard on `/verifica` routes — use controller redirect for better UX
- Do NOT implement approve/reject functionality — that is Story 3.3
- Do NOT implement conflict detection — that is Story 3.4
- Do NOT add `from __future__ import annotations` — Python 3.14+
- Do NOT use bare `except:` or catch `Exception` without re-raising
- Do NOT use `git` commands — use `jj` exclusively

### Library & Framework Requirements

**pydantic (>=2.0) — Structured Output schema definition (NEW dependency):**

| API | Usage | Import |
|---|---|---|
| `BaseModel` | Define `ConstraintTranslation` schema model | `from pydantic import BaseModel` |
| `ConfigDict` | Set `extra="forbid"` for `additionalProperties: false` | `from pydantic import ConfigDict` |
| `model_json_schema()` | Generate JSON Schema dict for OpenAI Structured Outputs | Class method on model |
| `model_validate_json(json_str)` | Parse + validate LLM response content | Class method on model |
| `model_dump()` | Convert validated instance to plain dict | Instance method |
| `ValidationError` | Catch schema validation failures | `from pydantic import ValidationError` |

**Pydantic usage pattern:**

```python
# Schema generation (module-level, once):
schema = ConstraintTranslation.model_json_schema()

# Response parsing (per-translation):
result = ConstraintTranslation.model_validate_json(content_string)
formal_repr = result.model_dump()  # plain dict for DB storage
```

**httpx (>=0.28.0) — Async HTTP client for LLM translation (existing dependency):**

| API | Usage | Import |
|---|---|---|
| `httpx.AsyncClient` | Async HTTP client context manager | `import httpx` |
| `client.post(url, json=..., headers=...)` | POST to `/chat/completions` | Method on client |
| `httpx.TimeoutException` | Catch request timeout (>10s) | `import httpx` |
| `httpx.RequestError` | Base class for all request errors | `import httpx` |

**httpx POST pattern for chat completions:**

```python
async with httpx.AsyncClient(timeout=10.0) as client:
    response = await client.post(
        url,
        json={"model": model_id, "messages": [...], "response_format": CONSTRAINT_RESPONSE_FORMAT},
        headers={"Authorization": f"Bearer {api_key}"},
    )
```

**Litestar (>=2.21.0) — Key APIs for this story:**

| API | Usage | Import |
|---|---|---|
| `Request.session` | Read LLM config from session | `from litestar import Request` |
| `Template` | Render verification template | `from litestar.response import Template` |
| `Redirect` | Redirect to `/impostazioni` when no LLM config | `from litestar.response import Redirect` |
| `get`, `post` | Route decorators for GET/POST `/verifica` | `from litestar import get, post` |
| `guards` | Route-level guard list | Route decorator param |
| `Provide` | DI provider registration | `from litestar.di import Provide` |

**Advanced Alchemy — Repository update pattern:**

```python
constraint.status = "translated"
constraint.formal_representation = result
await self.constraint_repo.update(constraint)
```

The `autocommit_handler_maker(commit_on_redirect=True)` commits the DB session on both 2xx and 3xx responses. No manual commit needed.

### File Structure Requirements

**Files to CREATE:**

```
templates/pages/timetable_verification.html     (CREATE: verification page with constraint cards)
```

**Files to UPDATE:**

```
pyproject.toml                                   (UPDATE: add pydantic>=2.0 to dependencies)
easyorario/exceptions.py                         (UPDATE: add LLMTranslationError)
easyorario/i18n/errors.py                        (UPDATE: add translation Italian messages)
easyorario/services/llm.py                       (UPDATE: add ConstraintTranslation model, CONSTRAINT_RESPONSE_FORMAT, TRANSLATION_SYSTEM_PROMPT, translate_constraint method)
easyorario/services/constraint.py                (UPDATE: add LLMService dependency, translate_pending_constraints method)
easyorario/controllers/constraint.py             (UPDATE: add POST /verifica and GET /verifica routes, import get_llm_config)
easyorario/app.py                                (UPDATE: update provide_constraint_service to accept llm_service param)
templates/pages/timetable_constraints.html       (UPDATE: change link to POST form, add translated/failed badges)
tests/services/test_llm.py                       (UPDATE: add translate_constraint tests)
tests/services/test_constraint.py                (UPDATE: add translate_pending_constraints tests)
tests/controllers/test_constraint.py             (UPDATE: add verification route tests)
```

**Files NOT to touch:**

```
easyorario/models/*                              (NO CHANGE — Constraint model already has formal_representation and status columns)
easyorario/repositories/*                        (NO CHANGE — existing update() method from Advanced Alchemy suffices)
easyorario/services/auth.py                      (NO CHANGE)
easyorario/services/timetable.py                 (NO CHANGE)
easyorario/controllers/auth.py                   (NO CHANGE)
easyorario/controllers/dashboard.py              (NO CHANGE)
easyorario/controllers/timetable.py              (NO CHANGE)
easyorario/controllers/settings.py               (NO CHANGE)
easyorario/guards/auth.py                        (NO CHANGE — requires_llm_config already exists from Story 3.1)
easyorario/config.py                             (NO CHANGE — no new env vars needed)
alembic/                                         (NO CHANGE — no new models or schema changes)
templates/base.html                              (NO CHANGE)
templates/pages/settings.html                    (NO CHANGE)
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
- `db_session`, `db_user`, `db_timetable` — for service/repo tests

New fixtures for this story:

```python
@pytest.fixture
async def db_constraint(db_session, db_timetable):
    """A pending constraint for db_timetable."""
    from easyorario.models.constraint import Constraint
    c = Constraint(
        timetable_id=db_timetable.id,
        natural_language_text="Prof. Rossi non può insegnare il lunedì mattina",
    )
    db_session.add(c)
    await db_session.flush()
    return c


@pytest.fixture
async def timetable_with_constraints(authenticated_client):
    """Create a timetable and add constraints via the API. Returns timetable_id."""
    csrf = _get_csrf_token(authenticated_client)
    # Create timetable
    resp = await authenticated_client.post(
        "/orario/nuovo",
        data={"class_identifier": "3A", "school_year": "2025-2026", "weekly_hours": "30",
              "subjects": "Matematica\nItaliano", "teachers": "Matematica: Prof. Rossi\nItaliano: Prof. Bianchi"},
        headers={"x-csrftoken": csrf},
        follow_redirects=False,
    )
    timetable_id = resp.headers["location"].split("/")[2]  # extract from /orario/{id}/vincoli
    # Add constraints
    for text in ["Prof. Rossi non può insegnare il lunedì mattina", "Matematica massimo 2 ore consecutive"]:
        await authenticated_client.post(
            f"/orario/{timetable_id}/vincoli",
            data={"text": text},
            headers={"x-csrftoken": csrf},
        )
    return timetable_id
```

**Mocking Strategy:**

- **Service tests for LLMService.translate_constraint:** Mock `httpx.AsyncClient.post` via `monkeypatch` to return canned responses (success, malformed, timeout, auth failure)
- **Service tests for ConstraintService.translate_pending_constraints:** Mock `LLMService.translate_constraint` to return a dict (don't re-test httpx)
- **Controller tests for POST/GET /verifica:** Mock `LLMService.translate_constraint` at the module level (don't re-test LLM API calls)

**Required Test Cases:**

| Test File | Test Name | Verifies |
|---|---|---|
| **test_llm.py** | `test_translate_constraint_with_valid_response_returns_dict` | Happy path: mocked 200 with valid JSON → returns dict |
| **test_llm.py** | `test_translate_constraint_with_malformed_json_raises` | `LLMTranslationError("llm_translation_malformed")` on invalid JSON |
| **test_llm.py** | `test_translate_constraint_with_invalid_schema_raises` | `LLMTranslationError("llm_translation_malformed")` on missing required fields |
| **test_llm.py** | `test_translate_constraint_with_timeout_raises` | `LLMTranslationError("llm_translation_timeout")` on TimeoutException |
| **test_llm.py** | `test_translate_constraint_with_connection_error_raises` | `LLMTranslationError("llm_translation_failed")` on RequestError |
| **test_llm.py** | `test_translate_constraint_with_auth_failure_raises` | `LLMConfigError("llm_auth_failed")` on 401 |
| **test_llm.py** | `test_translate_constraint_with_server_error_raises` | `LLMTranslationError("llm_translation_failed")` on 500 |
| **test_llm.py** | `test_translate_constraint_includes_timetable_context_in_prompt` | System prompt contains class_identifier, subjects, teachers |
| **test_llm.py** | `test_translate_constraint_sends_structured_output_format` | Request body includes `response_format` with `json_schema` type |
| **test_constraint.py** | `test_translate_pending_constraints_translates_all_pending` | All pending → translated, formal_representation stored |
| **test_constraint.py** | `test_translate_pending_constraints_partial_failure` | Some succeed, some fail — each gets correct status |
| **test_constraint.py** | `test_translate_pending_constraints_no_pending_returns_existing` | No pending constraints → returns existing without calling LLM |
| **test_constraint.py** | `test_translate_pending_constraints_updates_status_to_translated` | Status changes from "pending" to "translated" on success |
| **test_constraint.py** | `test_translate_pending_constraints_updates_status_to_failed` | Status changes from "pending" to "translation_failed" on LLMTranslationError |
| **test_constraint.py** | `test_translate_pending_constraints_skips_non_pending` | Already translated/verified constraints are not re-translated |
| **test_constraint.py** | `test_translate_pending_constraints_builds_timetable_context` | Timetable context passed to LLMService has correct keys |
| **test_constraint.py** | `test_constraint_service_accepts_llm_service_dependency` | ConstraintService constructor accepts LLMService |
| **test_constraint.py** (controller) | `test_post_verifica_translates_and_renders_page` | POST /verifica with mocked LLM → 200 with constraint cards |
| **test_constraint.py** (controller) | `test_post_verifica_as_professor_returns_403` | Role guard blocks Professor |
| **test_constraint.py** (controller) | `test_post_verifica_without_llm_config_redirects` | No LLM config in session → redirect to /impostazioni |
| **test_constraint.py** (controller) | `test_get_verifica_shows_translated_constraints` | GET /verifica shows already-translated constraints |
| **test_constraint.py** (controller) | `test_post_verifica_for_non_owned_timetable_returns_403` | Ownership check on timetable |
| **test_constraint.py** (controller) | `test_post_verifica_with_no_pending_shows_existing` | No pending → page renders with already-translated constraints |
| **test_constraint.py** (controller) | `test_post_verifica_shows_translation_counts` | Page shows translated_count and failed_count |
| **test_constraint.py** (controller) | `test_verification_page_shows_constraint_description` | Card shows `formal_representation.description` |
| **test_constraint.py** (controller) | `test_verification_page_shows_collapsible_json` | Card has `<details>` with JSON output |

**Mocking httpx in LLM service tests:**

```python
async def test_translate_constraint_with_valid_response_returns_dict(monkeypatch):
    valid_response = {
        "constraint_type": "teacher_unavailable",
        "description": "Prof. Rossi non è disponibile il lunedì nelle ore 1-3",
        "teacher": "Prof. Rossi",
        "subject": None,
        "days": ["lunedì"],
        "time_slots": [1, 2, 3],
        "max_consecutive_hours": None,
        "room": None,
        "notes": None,
    }

    async def mock_post(self, url, **kwargs):
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps(valid_response)}}]},
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    service = LLMService()
    result = await service.translate_constraint(
        base_url="https://api.example.com/v1",
        api_key="sk-test",
        model_id="gpt-4o",
        constraint_text="Prof. Rossi non può insegnare il lunedì mattina",
        timetable_context={
            "class_identifier": "3A",
            "weekly_hours": 30,
            "subjects": "Matematica, Italiano",
            "teachers": "Matematica: Prof. Rossi, Italiano: Prof. Bianchi",
            "max_slots": 5,
        },
    )
    assert result["constraint_type"] == "teacher_unavailable"
    assert result["teacher"] == "Prof. Rossi"
```

**Mocking LLMService in controller tests:**

```python
async def test_post_verifica_translates_and_renders_page(
    authenticated_client, timetable_with_constraints, monkeypatch,
):
    valid_result = {
        "constraint_type": "teacher_unavailable",
        "description": "Prof. Rossi non disponibile lunedì ore 1-3",
        "teacher": "Prof. Rossi", "subject": None, "days": ["lunedì"],
        "time_slots": [1, 2, 3], "max_consecutive_hours": None,
        "room": None, "notes": None,
    }

    async def mock_translate(self, **kwargs):
        return valid_result

    monkeypatch.setattr(
        "easyorario.services.llm.LLMService.translate_constraint",
        mock_translate,
    )

    # Set LLM config in session
    csrf = _get_csrf_token(authenticated_client)
    # ... (mock test_connectivity, POST to /impostazioni to set session config)

    response = await authenticated_client.post(
        f"/orario/{timetable_with_constraints}/vincoli/verifica",
        headers={"x-csrftoken": csrf},
    )
    assert response.status_code == 200
    assert "Prof. Rossi non disponibile" in response.text
```

**Setting LLM config in session for controller tests:**

Controller tests need LLM config in the session. Pattern: mock `test_connectivity` to succeed, POST to `/impostazioni` to store config, then proceed with verification tests.

```python
async def _set_llm_config(client, monkeypatch):
    """Helper: store LLM config in session via /impostazioni POST."""
    async def mock_test(self, base_url, api_key, model_id):
        return None  # success

    monkeypatch.setattr("easyorario.services.llm.LLMService.test_connectivity", mock_test)
    csrf = _get_csrf_token(client)
    await client.post(
        "/impostazioni",
        data={"base_url": "https://api.example.com/v1", "api_key": "sk-test", "model_id": "gpt-4o"},
        headers={"x-csrftoken": csrf},
    )
```

### Previous Story Intelligence

**From Story 3.1 (LLM Endpoint Configuration) — direct predecessor:**

- **LLMService is stateless** — no constructor dependencies, no DB access. New `translate_constraint()` follows the same pattern as `test_connectivity()`: receives all params, makes HTTP call, returns/raises
- **Session merge pattern** — `set_llm_config()` merges LLM keys into session alongside auth keys. Story 3.2 only reads config via `get_llm_config()` — no changes needed to session storage
- **`requires_llm_config` guard exists** but raises `NotAuthorizedException` → 403. Story 3.2 should NOT use this guard on verification routes — instead check in the controller and redirect to `/impostazioni`
- **httpx mocking pattern** — monkeypatch `httpx.AsyncClient.get` for GET requests. Story 3.2 needs `httpx.AsyncClient.post` for POST requests — same pattern, different method
- **Controller form pattern** — Story 3.1 used `Body(media_type=RequestEncodingType.URL_ENCODED)` for POST form data. Story 3.2's POST /verifica has no form data body — it's triggered by a submit button with only CSRF token
- **CSRF on all POST** — the verification form button needs `{{ csrf_input | safe }}` just like all other forms
- **`LLMConfigError` reuse** — Story 3.2 raises `LLMConfigError("llm_auth_failed")` for 401/403 during translation (same exception, config is wrong), and new `LLMTranslationError` for translation-specific failures
- **Endpoint URL pattern** — Story 3.1 used `{base_url}/models` (base_url includes `/v1`). Story 3.2 uses `{base_url}/chat/completions` (same convention — base_url includes version prefix)
- **29 tests in Story 3.1** — full suite was 128 tests. Story 3.2 adds ~25 tests, expected total ~153

**From Story 2.2 (Constraint Input) — provides the data model:**

- **Constraint model** has `formal_representation` (JSON, nullable) and `status` (String(20), default "pending") — both needed for translation. No schema changes needed
- **ConstraintController** already has `path="/orario/{timetable_id:uuid}/vincoli"` — new routes add `/verifica` under this path
- **Ownership check pattern** — `timetable.owner_id != request.user.id` → raise `NotAuthorizedException`. Same check needed on verification routes
- **PRG pattern** — Story 2.2 POST redirects back to GET. Story 3.2 POST renders Template directly (no redirect after translation — user sees results immediately)
- **`has_pending` context variable** — constraint list page already computes this and shows "Verifica vincoli" button conditionally. Story 3.2 changes the link to a POST form button
- **Badge patterns** — `<span badge>in attesa</span>`, `<span badge data-variant="success">verificato</span>`, etc. Story 3.2 adds `tradotto` (warning variant) and `errore traduzione` (error variant)

### Git Intelligence

**Recent commits (Story 3.1):**
```
3266ed5 stuff to claude
f8489c3 story 3.1: code review fixes -- remove unused import, add guard tests, add POST 403 test, add HTML required attrs
9927233 story 3.1: finalize -- update story and sprint status to review
2c38929 story 3.1: settings controller, template, nav link, DI wiring (tasks 5-7)
4fbc2a1 story 3.1: add httpx dependency, LLM exceptions, i18n messages, LLM service with connectivity test and session helpers, requires_llm_config guard (tasks 1-4)
```

**Commit patterns to follow:**
- Atomic commits per task group: `story 3.2: description (tasks N-M)`
- `just check` before every commit (format + lint + typecheck)
- `just test` separately to verify tests pass
- Create bookmark: `jj bookmark create story-3.2-constraint-translation`

**Suggested commit sequence for Story 3.2:**
1. `story 3.2: add pydantic dependency, LLMTranslationError, i18n messages (task 1)`
2. `story 3.2: ConstraintTranslation schema, system prompt, translate_constraint method (task 2)`
3. `story 3.2: translate_pending_constraints in ConstraintService, update DI wiring (tasks 3, 6)`
4. `story 3.2: verification routes in ConstraintController, templates (tasks 4-5)`
5. `story 3.2: comprehensive tests for translation service, constraint service, and controller (task 7)`

### Project Structure Notes

- **Flat layout confirmed:** `easyorario/` at project root (no `src/`). The architecture doc mentions `src/easyorario/` but the actual project uses `easyorario/` directly. Follow what exists, not the architecture doc.
- **Tests at `tests/`** at project root, mirroring `easyorario/` structure.
- **Templates at `templates/`** at project root, pages under `templates/pages/`.
- **No new directories needed** — all new files go into existing directories.
- **No database migrations needed** — Constraint model already has `formal_representation` (JSON, nullable) and `status` fields. No schema changes.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.2]
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 3 overview]
- [Source: _bmad-output/planning-artifacts/architecture.md#Core Architectural Decisions — LLM integration boundary]
- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure & Boundaries — services/llm.py]
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns & Consistency Rules]
- [Source: _bmad-output/planning-artifacts/architecture.md#API & Communication Patterns — async operations]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Constraint Verification]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Site Map — /orario/{id}/vincoli/verifica]
- [Source: _bmad-output/implementation-artifacts/3-1-llm-endpoint-configuration.md — LLMService, session patterns, httpx mocking]
- [Source: easyorario/services/llm.py — existing LLMService with test_connectivity, get_llm_config, set_llm_config]
- [Source: easyorario/services/constraint.py — existing ConstraintService with add_constraint, list_constraints]
- [Source: easyorario/controllers/constraint.py — existing ConstraintController with list/add routes]
- [Source: easyorario/models/constraint.py — Constraint model with formal_representation and status fields]
- [Source: easyorario/repositories/constraint.py — ConstraintRepository with get_by_timetable]
- [Source: easyorario/exceptions.py — domain exception hierarchy]
- [Source: easyorario/i18n/errors.py — Italian message mappings]
- [Source: easyorario/guards/auth.py — requires_llm_config guard]
- [Source: easyorario/app.py — DI wiring, autocommit handler, session auth]
- [Source: templates/pages/timetable_constraints.html — constraint list with "Verifica vincoli" link]
- [Source: templates/base.html — nav layout]
- [Source: tests/conftest.py — test fixtures and helpers]
- [Source: CLAUDE.md#Architecture]
- [Source: CLAUDE.md#Commands]
- [Source: OpenAI API — Structured Outputs: https://developers.openai.com/api/docs/guides/structured-outputs/]
- [Source: Pydantic JSON Schema: https://docs.pydantic.dev/latest/concepts/json_schema/]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
