# Story 3.3: Constraint Verification & Approval

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->
<!-- Prerequisites: Story 3.2 (Constraint Translation via LLM) MUST be completed before starting this story. -->

## Story

As a Responsible Professor,
I want to review each translated constraint and approve or reject it,
so that I can trust the system's interpretation before generating a timetable.

## Acceptance Criteria

1. **Given** I am on `/orario/{id}/vincoli/verifica` with translated constraints **When** I view the page **Then** I see a card for each constraint showing: original Italian text, structured human-readable interpretation, and a collapsible `<details>` section with the Z3 formal representation

2. **Given** I am reviewing a constraint card with status "translated" **When** I click "Approva" **Then** the constraint status changes to "verified", its badge turns green, and I am redirected back to the verification page

3. **Given** I am reviewing a constraint card with status "translated" **When** I click "Rifiuta" **Then** the constraint status changes to "rejected" with a red badge, and I can go back to the constraint list to edit the original text and resubmit for re-translation

4. **Given** all constraints have been reviewed **When** at least one is verified **Then** I see a "Genera orario" link/button pointing to `/orario/{id}/genera` (non-functional until Epic 4)

5. **Given** I am a Professor (not Responsible Professor) **When** I try to approve or reject a constraint **Then** I receive a 403 Forbidden response

6. **Given** I try to approve or reject a constraint on a timetable I don't own **When** the request is processed **Then** I receive a 403 Forbidden response

7. **Given** I try to approve a constraint that is not in "translated" status **When** the request is processed **Then** the request fails gracefully and I am redirected back to the verification page with an error message

## Tasks / Subtasks

- [ ] Task 1: Add Italian messages and exception for invalid status transition (AC: #7)
  - [ ] 1.1 Add Italian messages to `easyorario/i18n/errors.py`: `constraint_approved` ("Vincolo approvato"), `constraint_rejected` ("Vincolo rifiutato"), `constraint_not_translatable` ("Il vincolo deve essere nello stato 'tradotto' per essere approvato o rifiutato")
  - [ ] 1.2 No new exception class needed — use `InvalidConstraintDataError` with `"constraint_not_translatable"` error_key for invalid status transitions

- [ ] Task 2: Add `verify_constraint` and `reject_constraint` methods to ConstraintService (AC: #2, #3, #7)
  - [ ] 2.1 Implement `async verify_constraint(self, *, constraint_id: uuid.UUID, timetable_id: uuid.UUID) -> Constraint` — fetches constraint by ID, validates `constraint.timetable_id == timetable_id`, validates `constraint.status == "translated"`, sets status to `"verified"`, updates in repository, returns constraint
  - [ ] 2.2 Implement `async reject_constraint(self, *, constraint_id: uuid.UUID, timetable_id: uuid.UUID) -> Constraint` — same pattern, sets status to `"rejected"`, clears `formal_representation` to None (so re-translation produces fresh result)
  - [ ] 2.3 Raise `InvalidConstraintDataError("constraint_not_translatable")` if constraint status is not `"translated"` for either operation

- [ ] Task 3: Add approve/reject POST routes to ConstraintController (AC: #2, #3, #5, #6, #7)
  - [ ] 3.1 Add `POST /orario/{timetable_id}/vincoli/{constraint_id}/approva` route — guards: `requires_responsible_professor`. Loads timetable, checks ownership, calls `constraint_service.verify_constraint()`, redirects to GET `/verifica`
  - [ ] 3.2 Add `POST /orario/{timetable_id}/vincoli/{constraint_id}/rifiuta` route — same pattern, calls `constraint_service.reject_constraint()`, redirects to GET `/verifica`
  - [ ] 3.3 Handle `InvalidConstraintDataError` — redirect to GET `/verifica` (error displayed via badge state)

- [ ] Task 4: Update verification template with approve/reject buttons and "Genera orario" link (AC: #1, #2, #3, #4)
  - [ ] 4.1 Add approve/reject POST form buttons to constraint cards with status "translated" — "Approva" (primary button) and "Rifiuta" (secondary outline button) in a horizontal stack
  - [ ] 4.2 Update rejected constraint display — show `formal_representation.description` if available, add "Modifica e riprova" link back to constraint list
  - [ ] 4.3 Update verification page status counts — add `verified_count` to the summary badge row
  - [ ] 4.4 Add "Genera orario" link at the bottom when `verified_count >= 1` and all constraints have been reviewed (no "translated" remaining) — links to `/orario/{id}/genera` (non-functional placeholder until Epic 4)

- [ ] Task 5: Update constraint list template for rejected constraints (AC: #3)
  - [ ] 5.1 When a constraint has status "rejected", show it in the constraint list with the "rifiutato" badge already present (no changes needed — badge already exists). Verify the rejected constraint can be resubmitted via the existing "add constraint" flow (user edits text, submits new constraint, original rejected one stays in history)

- [ ] Task 6: Write tests (AC: #1-#7)
  - [ ] 6.1 `tests/services/test_constraint.py` (additions): test verify_constraint sets status to verified, test reject_constraint sets status to rejected and clears formal_representation, test verify non-translated constraint raises InvalidConstraintDataError, test reject non-translated constraint raises InvalidConstraintDataError, test verify constraint validates timetable ownership, test reject constraint validates timetable ownership
  - [ ] 6.2 `tests/controllers/test_constraint.py` (additions): test POST approva sets verified and redirects, test POST rifiuta sets rejected and redirects, test POST approva as Professor returns 403, test POST rifiuta as Professor returns 403, test POST approva for non-owned timetable returns 403, test POST approva for non-translated constraint redirects, test verification page shows approve/reject buttons on translated cards, test verification page shows genera orario link when all verified, test verification page hides genera orario when translated constraints remain

## Dev Notes

### Constraint Verification Flow — Core Design

**This story completes the constraint review cycle.** Story 3.2 translated constraints; Story 3.3 lets the user approve or reject each translation. The flow is:

1. User arrives at `/orario/{id}/vincoli/verifica` (via GET or POST from Story 3.2)
2. Each translated constraint card now shows "Approva" and "Rifiuta" buttons
3. User clicks "Approva" → POST to `/{constraint_id}/approva` → status → "verified" → redirect back to `/verifica`
4. User clicks "Rifiuta" → POST to `/{constraint_id}/rifiuta` → status → "rejected" → redirect back to `/verifica`
5. Once all constraints reviewed (no "translated" remaining) and >=1 verified → "Genera orario" link appears

**Status transitions this story implements:**
- `translated` → `verified` (user approves)
- `translated` → `rejected` (user rejects)

**What happens to rejected constraints:**
- Status set to "rejected", `formal_representation` cleared to None
- On the constraint list page (`/vincoli`), the rejected constraint shows with "rifiutato" badge
- User can go back to constraint list and add a new constraint with rephrased text
- The rejected constraint remains in the list as history (not deleted)
- If the user triggers re-translation (POST `/verifica`), rejected constraints are NOT re-translated (only `pending` and `translation_failed` are — per Story 3.2 service logic)

### Service Methods

```python
async def verify_constraint(
    self,
    *,
    constraint_id: uuid.UUID,
    timetable_id: uuid.UUID,
) -> Constraint:
    """Approve a translated constraint."""
    constraint = await self.constraint_repo.get(constraint_id)
    if constraint.timetable_id != timetable_id:
        raise NotAuthorizedException(detail="Insufficient permissions")
    if constraint.status != "translated":
        raise InvalidConstraintDataError("constraint_not_translatable")
    constraint.status = "verified"
    return await self.constraint_repo.update(constraint)


async def reject_constraint(
    self,
    *,
    constraint_id: uuid.UUID,
    timetable_id: uuid.UUID,
) -> Constraint:
    """Reject a translated constraint."""
    constraint = await self.constraint_repo.get(constraint_id)
    if constraint.timetable_id != timetable_id:
        raise NotAuthorizedException(detail="Insufficient permissions")
    if constraint.status != "translated":
        raise InvalidConstraintDataError("constraint_not_translatable")
    constraint.status = "rejected"
    constraint.formal_representation = None
    return await self.constraint_repo.update(constraint)
```

**Key decisions:**
- **Timetable ownership check in service**: The `constraint.timetable_id != timetable_id` check prevents cross-timetable manipulation. The controller also checks `timetable.owner_id != request.user.id`, so this is defense in depth.
- **`NotAuthorizedException` from service**: Reuses Litestar's built-in exception. The controller's ownership check should catch this first, but the service check provides safety.
- **Status guard**: Only `"translated"` constraints can be approved/rejected. Attempting to approve a `"pending"`, `"translation_failed"`, `"verified"`, or `"rejected"` constraint raises `InvalidConstraintDataError`.
- **Clear `formal_representation` on reject**: Ensures re-translation produces a clean result. The rejected constraint's interpretation is gone — the user saw it and disagreed.

### Controller Routes

```python
@post("/{constraint_id:uuid}/approva", guards=[requires_responsible_professor])
async def approve_constraint(
    self,
    request: Request,
    timetable_id: uuid.UUID,
    constraint_id: uuid.UUID,
    timetable_repo: TimetableRepository,
    constraint_service: ConstraintService,
) -> Redirect:
    """Approve a translated constraint (set status to verified)."""
    timetable = await timetable_repo.get(timetable_id)
    if timetable.owner_id != request.user.id:
        raise NotAuthorizedException(detail="Insufficient permissions")
    await constraint_service.verify_constraint(
        constraint_id=constraint_id,
        timetable_id=timetable_id,
    )
    return Redirect(path=f"/orario/{timetable_id}/vincoli/verifica")


@post("/{constraint_id:uuid}/rifiuta", guards=[requires_responsible_professor])
async def reject_constraint(
    self,
    request: Request,
    timetable_id: uuid.UUID,
    constraint_id: uuid.UUID,
    timetable_repo: TimetableRepository,
    constraint_service: ConstraintService,
) -> Redirect:
    """Reject a translated constraint (set status to rejected)."""
    timetable = await timetable_repo.get(timetable_id)
    if timetable.owner_id != request.user.id:
        raise NotAuthorizedException(detail="Insufficient permissions")
    await constraint_service.reject_constraint(
        constraint_id=constraint_id,
        timetable_id=timetable_id,
    )
    return Redirect(path=f"/orario/{timetable_id}/vincoli/verifica")
```

**Key decisions:**
- **POST + Redirect (PRG pattern)**: Both routes redirect to GET `/verifica` to prevent form resubmission on refresh. This matches the pattern established in Story 2.2 for adding constraints.
- **Both routes under ConstraintController path**: They naturally nest under `/orario/{timetable_id}/vincoli/{constraint_id}/approva|rifiuta`. Litestar routes them via the existing ConstraintController.
- **No form data body**: The routes only need the path parameters (timetable_id and constraint_id) plus CSRF token. No `Body()` parameter.
- **`InvalidConstraintDataError` handling**: If the constraint status is not "translated", the service raises this exception. The existing exception handler in `app.py` will render a 400 error page. Alternatively, the controller could catch it and redirect — but since this only happens with stale pages or manual URL crafting, the default error handler is sufficient.

### Template Updates — Verification Page

Add approve/reject buttons to translated constraint cards and "Genera orario" link:

```html
{% if constraint.status == "translated" and constraint.formal_representation %}
<p>
  <span badge data-variant="warning">tradotto</span>
  <strong>Interpretazione:</strong> {{ constraint.formal_representation.description }}
</p>
<details>
  <summary>Dettagli tecnici (JSON)</summary>
  <pre><code>{{ constraint.formal_representation | tojson(indent=2) }}</code></pre>
</details>
<div class="hstack">
  <form method="post" action="/orario/{{ timetable.id }}/vincoli/{{ constraint.id }}/approva">
    {{ csrf_input | safe }}
    <button type="submit" class="small">Approva</button>
  </form>
  <form method="post" action="/orario/{{ timetable.id }}/vincoli/{{ constraint.id }}/rifiuta">
    {{ csrf_input | safe }}
    <button type="submit" class="small outline">Rifiuta</button>
  </form>
</div>
{% elif constraint.status == "rejected" %}
<p>
  <span badge data-variant="error">rifiutato</span>
  {% if constraint.formal_representation %}
  {{ constraint.formal_representation.description }}
  {% endif %}
</p>
<p><a href="/orario/{{ timetable.id }}/vincoli">Modifica e riprova</a></p>
{% endif %}
```

**"Genera orario" link logic at the bottom of the page:**

```html
{% set has_translated = constraints | selectattr("status", "equalto", "translated") | list | length > 0 %}
{% set verified_count_val = constraints | selectattr("status", "equalto", "verified") | list | length %}

{% if verified_count_val >= 1 and not has_translated %}
<a href="/orario/{{ timetable.id }}/genera" class="button w-100">Genera orario</a>
{% endif %}
```

The "Genera orario" button appears ONLY when:
- At least 1 constraint is verified
- No "translated" constraints remain (all have been reviewed — either verified or rejected)

This prevents generating a timetable with unreviewed translations.

### Updated Verification Page Count Badges

Update the count badges at the top to include verified count:

```html
{% if translated_count or failed_count or verified_count %}
<p>
  {% if verified_count %}<span badge data-variant="success">{{ verified_count }} verificati</span>{% endif %}
  {% if translated_count %}<span badge data-variant="warning">{{ translated_count }} da verificare</span>{% endif %}
  {% if failed_count %}<span badge data-variant="error">{{ failed_count }} errori</span>{% endif %}
</p>
{% endif %}
```

The controller must compute and pass `verified_count` alongside `translated_count` and `failed_count`.

### Architecture Compliance

**Boundary Rules — MUST follow:**

| Rule | This Story's Application |
|---|---|
| Controller → Service → Repository (one-way) | ConstraintController calls ConstraintService methods. Controller NEVER calls ConstraintRepository directly. |
| Controllers handle HTTP only — no business logic | Controller checks ownership, delegates approval/rejection to ConstraintService. Status validation is in the service. |
| Guards enforce authorization declaratively | `requires_responsible_professor` guard on both approve and reject routes. |
| Italian user-facing text, English code/logs | Template text in Italian. Python identifiers, comments, log messages in English. |
| `structlog` for all logging, never `print()` | Log verification events: `constraint_verified`, `constraint_rejected`. NEVER log sensitive data. |
| Use Litestar DI, never manual instantiation | ConstraintService already wired via DI. No new DI changes needed. |
| `snake_case` for Python/JSON, `kebab-case` for URLs | URLs: `/approva`, `/rifiuta`. Python: `verify_constraint`, `reject_constraint`. |
| `jj` for VCS, never raw `git` | All commits via `jj commit -m "message"`. |

**Anti-Patterns — NEVER do:**

- Do NOT implement conflict detection — that is Story 3.4
- Do NOT implement the actual generation endpoint — that is Story 4.1 (only add the non-functional link)
- Do NOT add `from __future__ import annotations` — Python 3.14+
- Do NOT use bare `except:` or catch `Exception` without re-raising
- Do NOT use `git` commands — use `jj` exclusively
- Do NOT add new DI providers unless absolutely necessary — existing wiring is sufficient
- Do NOT delete rejected constraints — they stay in the list as history

### Library & Framework Requirements

**Litestar (>=2.21.0) — Key APIs for this story:**

| API | Usage | Import |
|---|---|---|
| `Request.user.id` | Ownership check on timetable | `from litestar import Request` |
| `Redirect` | PRG pattern after approve/reject | `from litestar.response import Redirect` |
| `post` | Route decorator for POST approve/reject | `from litestar import post` |
| `guards` | Route-level guard list | Route decorator param |
| `NotAuthorizedException` | Ownership violation | `from litestar.exceptions import NotAuthorizedException` |

**Advanced Alchemy — Repository operations:**

| API | Usage |
|---|---|
| `constraint_repo.get(constraint_id)` | Fetch single constraint by UUID |
| `constraint_repo.update(constraint)` | Persist status change |

The `autocommit_handler_maker(commit_on_redirect=True)` already configured in app.py commits the DB session on 3xx redirects. This is critical — without it, the status changes from approve/reject would not persist because the response is a redirect (3xx), not 2xx.

### File Structure Requirements

**Files to CREATE:**

```
(none — no new files needed)
```

**Files to UPDATE:**

```
easyorario/i18n/errors.py                        (UPDATE: add 3 verification messages)
easyorario/services/constraint.py                (UPDATE: add verify_constraint and reject_constraint methods)
easyorario/controllers/constraint.py             (UPDATE: add POST /{constraint_id}/approva and /rifiuta routes, update show_verification to pass verified_count)
templates/pages/timetable_verification.html      (UPDATE: add approve/reject buttons, genera orario link, verified count badge)
tests/services/test_constraint.py                (UPDATE: add verification service tests)
tests/controllers/test_constraint.py             (UPDATE: add approval/rejection controller tests)
```

**Files NOT to touch:**

```
easyorario/models/*                              (NO CHANGE — Constraint model already supports all statuses)
easyorario/repositories/*                        (NO CHANGE — existing get() and update() suffice)
easyorario/app.py                                (NO CHANGE — DI wiring already correct)
easyorario/guards/auth.py                        (NO CHANGE)
easyorario/exceptions.py                         (NO CHANGE — reusing InvalidConstraintDataError)
easyorario/services/llm.py                       (NO CHANGE)
easyorario/controllers/auth.py                   (NO CHANGE)
easyorario/controllers/dashboard.py              (NO CHANGE)
easyorario/controllers/timetable.py              (NO CHANGE)
easyorario/controllers/settings.py               (NO CHANGE)
templates/base.html                              (NO CHANGE)
templates/pages/timetable_constraints.html       (NO CHANGE — badges for verified/rejected already exist)
alembic/                                         (NO CHANGE — no schema changes)
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

**Mocking Strategy:**

- **Service tests**: No mocking needed. Create Constraint objects directly in the DB via repository, call `verify_constraint` / `reject_constraint`, assert status changes.
- **Controller tests**: Mock `LLMService.translate_constraint` for the setup step (creating translated constraints via POST `/verifica`), then test approve/reject routes without mocking. Alternatively, create constraints directly in the DB and set `status="translated"` + `formal_representation={...}` for simpler setup.

**Required Test Cases:**

| Test File | Test Name | Verifies |
|---|---|---|
| **test_constraint.py** (service) | `test_verify_constraint_sets_status_to_verified` | Happy path: translated → verified |
| **test_constraint.py** (service) | `test_reject_constraint_sets_status_to_rejected` | Happy path: translated → rejected, formal_representation cleared |
| **test_constraint.py** (service) | `test_verify_constraint_non_translated_raises` | Status guard: pending/failed/verified/rejected → InvalidConstraintDataError |
| **test_constraint.py** (service) | `test_reject_constraint_non_translated_raises` | Status guard: pending/failed/verified/rejected → InvalidConstraintDataError |
| **test_constraint.py** (service) | `test_verify_constraint_wrong_timetable_raises` | Timetable ownership in service layer |
| **test_constraint.py** (service) | `test_reject_constraint_wrong_timetable_raises` | Timetable ownership in service layer |
| **test_constraint.py** (controller) | `test_post_approva_sets_verified_and_redirects` | POST approve → status verified, redirect to /verifica |
| **test_constraint.py** (controller) | `test_post_rifiuta_sets_rejected_and_redirects` | POST reject → status rejected, redirect to /verifica |
| **test_constraint.py** (controller) | `test_post_approva_as_professor_returns_403` | Role guard blocks Professor |
| **test_constraint.py** (controller) | `test_post_rifiuta_as_professor_returns_403` | Role guard blocks Professor |
| **test_constraint.py** (controller) | `test_post_approva_non_owned_timetable_returns_403` | Ownership check on timetable |
| **test_constraint.py** (controller) | `test_post_approva_non_translated_constraint_returns_error` | Status guard via service exception |
| **test_constraint.py** (controller) | `test_verification_page_shows_approve_reject_buttons` | UI: buttons present on translated cards |
| **test_constraint.py** (controller) | `test_verification_page_shows_genera_link_when_all_verified` | "Genera orario" link when >=1 verified, 0 translated remaining |
| **test_constraint.py** (controller) | `test_verification_page_hides_genera_link_when_translated_remain` | No "Genera orario" when translated constraints still exist |

**Controller Test Setup Pattern:**

For controller tests that need translated constraints, the simplest approach is to mock the LLM translation and go through the full flow:

```python
async def _create_translated_constraint(client, timetable_id, monkeypatch):
    """Helper: add a constraint and translate it via mocked LLM."""
    csrf = _get_csrf_token(client)

    # Add constraint
    await client.post(
        f"/orario/{timetable_id}/vincoli",
        data={"text": "Prof. Rossi non può il lunedì"},
        headers={"x-csrftoken": csrf},
    )

    # Mock LLM and translate
    async def mock_translate(self, **kwargs):
        return {
            "constraint_type": "teacher_unavailable",
            "description": "Prof. Rossi non disponibile il lunedì",
            "teacher": "Prof. Rossi",
            "subject": None,
            "days": ["lunedì"],
            "time_slots": None,
            "max_consecutive_hours": None,
            "room": None,
            "notes": None,
        }

    monkeypatch.setattr(
        "easyorario.services.llm.LLMService.translate_constraint",
        mock_translate,
    )

    # Set LLM config and translate
    await _set_llm_config(client, monkeypatch)
    await client.post(
        f"/orario/{timetable_id}/vincoli/verifica",
        headers={"x-csrftoken": csrf},
    )
```

### Previous Story Intelligence

**From Story 3.2 (Constraint Translation via LLM) — direct predecessor:**

- **Template already has forward-compatible code**: The verification template (`timetable_verification.html`) already renders "verified" and "rejected" badges — just needs buttons to trigger the status change
- **Status "translated" is the target**: Only constraints with `status == "translated"` can be approved/rejected. The service from 3.2 sets this status on successful translation
- **PRG pattern for redirects**: Story 3.2 POST `/verifica` renders the template directly (no redirect). Story 3.3 approve/reject routes use PRG (redirect to GET `/verifica`) which is the correct pattern for state-changing operations
- **`autocommit_handler_maker(commit_on_redirect=True)`**: Critical for Story 3.3 — without this, the status changes from approve/reject would not persist because the response is a redirect (3xx). This was configured in Story 1.1 (app.py)
- **`constraint.formal_representation.description`**: Template accesses nested dict key. This works because `formal_representation` is a JSON column that stores a dict. Jinja2 supports attribute access on dicts
- **161 tests currently passing**: Story 3.3 should add ~15 tests, expected total ~176
- **LLM config session pattern**: `get_llm_config(request.session)` reads config set by POST `/impostazioni`. Controller tests need to set this up via `_set_llm_config()` helper before translation routes work
- **CSRF is required on all POSTs**: All approve/reject forms must include `{{ csrf_input | safe }}`
- **Ownership check pattern**: `timetable.owner_id != request.user.id` → raise `NotAuthorizedException`. Same check on all routes

### Git Intelligence

**Recent commits (Story 3.2):**
```
cd8ae33 basic readme
61708af story 3.2: code review fixes -- retry button, flash message, fail-fast, ownership ordering, 5 new tests
07a7f81 story 3.2: finalize -- update story and sprint status to review
ca97862 story 3.2: verification routes in ConstraintController, templates (tasks 4-5)
9ed91f3 story 3.2: translate_pending_constraints in ConstraintService, update DI wiring (tasks 3, 6)
```

**Commit patterns to follow:**
- Atomic commits per task group: `story 3.3: description (tasks N-M)`
- `just check` before every commit (format + lint + typecheck)
- `just test` separately to verify tests pass
- Create bookmark: `jj bookmark create story-3.3-constraint-verification`

**Suggested commit sequence for Story 3.3:**
1. `story 3.3: add i18n messages for verification (task 1)`
2. `story 3.3: verify_constraint and reject_constraint in ConstraintService (task 2)`
3. `story 3.3: approve/reject routes in ConstraintController (task 3)`
4. `story 3.3: update verification template with buttons and genera link (tasks 4-5)`
5. `story 3.3: tests for verification service methods and controller routes (task 6)`

### Project Structure Notes

- **Flat layout confirmed:** `easyorario/` at project root (no `src/`). The architecture doc mentions `src/easyorario/` but the actual project uses `easyorario/` directly. Follow what exists, not the architecture doc.
- **Tests at `tests/`** at project root, mirroring `easyorario/` structure.
- **Templates at `templates/`** at project root, pages under `templates/pages/`.
- **No new files or directories needed** — all changes are to existing files.
- **No database migrations needed** — Constraint model already has `status` (String(20)) that supports any status value.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.3]
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 3 overview]
- [Source: _bmad-output/planning-artifacts/architecture.md#Core Architectural Decisions — Controller→Service→Repository]
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns & Consistency Rules]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Constraint Verification]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Key Interaction Patterns]
- [Source: _bmad-output/implementation-artifacts/3-2-constraint-translation-via-llm.md — all sections]
- [Source: easyorario/controllers/constraint.py — existing ConstraintController with list/add/translate/show_verification routes]
- [Source: easyorario/services/constraint.py — existing ConstraintService with add_constraint, list_constraints, translate_pending_constraints]
- [Source: easyorario/models/constraint.py — Constraint model with formal_representation, status fields]
- [Source: easyorario/repositories/constraint.py — ConstraintRepository with get_by_timetable, inherited get/update]
- [Source: easyorario/exceptions.py — InvalidConstraintDataError]
- [Source: easyorario/i18n/errors.py — Italian message mappings]
- [Source: easyorario/guards/auth.py — requires_responsible_professor guard]
- [Source: easyorario/app.py — DI wiring, autocommit_handler_maker(commit_on_redirect=True)]
- [Source: templates/pages/timetable_verification.html — current verification template with forward-compatible verified/rejected blocks]
- [Source: templates/pages/timetable_constraints.html — constraint list with all status badges]
- [Source: tests/conftest.py — test fixtures and helpers]
- [Source: CLAUDE.md#Architecture]
- [Source: CLAUDE.md#Commands]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
