# Story 3.4: Pre-Solve Constraint Conflict Detection

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->
<!-- Prerequisites: Story 3.3 (Constraint Verification & Approval) MUST be completed before starting this story. -->

## Story

As a Responsible Professor,
I want the system to detect obvious constraint conflicts before generation,
so that I can fix issues without waiting for the solver to fail.

## Acceptance Criteria

1. **Given** I have multiple verified constraints **When** the system checks for conflicts **Then** it identifies teacher double-bookings (same teacher assigned to conflicting time slots) with 100% accuracy

2. **Given** I have multiple verified constraints **When** the system checks for conflicts **Then** it identifies hour-total mismatches (subject hours in constraints exceed `weekly_hours` for the timetable) with 100% accuracy

3. **Given** a conflict is detected **When** I view the constraints page (`/orario/{id}/vincoli`) **Then** I see an Italian warning alert identifying the conflicting constraints by their description text

4. **Given** no conflicts are detected **When** I view the constraints page **Then** no warning is shown and generation can proceed normally

5. **Given** I have no verified constraints **When** I view the constraints page **Then** no conflict check is performed and no warning is shown

6. **Given** conflict detection encounters a constraint with missing or malformed `formal_representation` **When** the check runs **Then** that constraint is skipped gracefully (no crash) and conflicts among remaining constraints are still reported

## Tasks / Subtasks

- [x] Task 1: Add conflict detection logic to ConstraintService (AC: #1, #2, #5, #6)
  - [x] 1.1 Add `detect_conflicts(constraints: list[Constraint], timetable: Timetable) -> list[ConflictWarning]` method to ConstraintService
  - [x] 1.2 Implement teacher double-booking detection: find pairs of verified constraints where the same teacher is marked unavailable/scheduled on overlapping days+time_slots
  - [x] 1.3 Implement hour-total mismatch detection: sum up subject-related hour allocations from verified constraints and compare against `timetable.weekly_hours`
  - [x] 1.4 Define `ConflictWarning` as a simple dataclass with `conflict_type: str`, `message: str` (Italian), `constraint_descriptions: list[str]`
  - [x] 1.5 Skip constraints where `formal_representation` is None or missing required fields — log a warning via structlog, do not crash

- [x] Task 2: Add Italian i18n messages for conflict warnings (AC: #3)
  - [x] 2.1 Add conflict message templates to `easyorario/i18n/errors.py`: `conflict_teacher_double_booking`, `conflict_hour_total_mismatch`

- [x] Task 3: Integrate conflict detection into ConstraintController (AC: #3, #4, #5)
  - [x] 3.1 Update `GET /orario/{timetable_id}/vincoli` (list_constraints) to call `detect_conflicts()` on verified constraints and pass warnings to template context
  - [x] 3.2 Update `GET /orario/{timetable_id}/vincoli/verifica` (show_verification) to also run conflict detection and pass warnings to template context

- [x] Task 4: Update templates to display conflict warnings (AC: #3, #4)
  - [x] 4.1 Update `timetable_constraints.html` — add an Oat UI alert section (warning variant) above the constraints list that renders each conflict warning with its message and referenced constraint descriptions
  - [x] 4.2 Update `timetable_verification.html` — add the same warning alert section above the constraint cards

- [x] Task 5: Write tests (AC: #1-#6)
  - [x] 5.1 `tests/services/test_constraint.py` (additions): test detect_conflicts finds teacher double-booking, test detect_conflicts finds hour-total mismatch, test detect_conflicts returns empty for non-conflicting constraints, test detect_conflicts skips non-verified constraints, test detect_conflicts skips constraints with None formal_representation, test detect_conflicts with no constraints returns empty
  - [x] 5.2 `tests/controllers/test_constraint.py` (additions): test constraints page shows warning when conflicts detected, test constraints page shows no warning when no conflicts, test verification page shows warning when conflicts detected

## Dev Notes

### Conflict Detection — Core Design

**This story implements pre-solve conflict detection as a lightweight, rule-based analysis.** The Z3 solver does not exist yet (it's Story 4.1), so this detection operates purely on the structured `formal_representation` JSON stored on verified constraints. The goal is to catch **obvious** errors before the user triggers generation — not to replicate the full solver.

**Two conflict types to detect (per epics FR-3):**

1. **Teacher double-booking:** Two verified constraints assign the same teacher to conflicting time slots on the same day. For example:
   - Constraint A: "Prof. Rossi insegna matematica il lunedì alla 1a e 2a ora"
   - Constraint B: "Prof. Rossi insegna fisica il lunedì alla 2a ora"
   - Conflict: Prof. Rossi is double-booked on lunedì, 2nd slot

2. **Hour-total mismatch:** The sum of subject hours implied by verified constraints exceeds the timetable's `weekly_hours`. For example:
   - Timetable has `weekly_hours: 27`
   - Constraint A: "Matematica 6 ore settimanali"
   - Constraint B: "Italiano 6 ore settimanali"
   - ... (total exceeds 27)
   - This checks the `max_consecutive_hours` or time_slot allocations don't exceed capacity

**What this does NOT detect:**
- Complex scheduling infeasibilities (that's the solver's job)
- Preference conflicts (soft constraints)
- Room conflicts (not enough information in current constraint types)

### ConflictWarning Dataclass

```python
from dataclasses import dataclass


@dataclass
class ConflictWarning:
    """A detected pre-solve conflict between constraints."""
    conflict_type: str  # "teacher_double_booking" or "hour_total_mismatch"
    message: str  # Italian human-readable description
    constraint_descriptions: list[str]  # descriptions of the conflicting constraints
```

This is a simple value object — not a model, not persisted. Created fresh on each page load from the verified constraints.

### Detection Algorithm — Teacher Double-Booking

```python
def _detect_teacher_double_bookings(
    self,
    verified: list[Constraint],
) -> list[ConflictWarning]:
    """Find verified constraints that double-book a teacher on the same day+slot."""
    warnings: list[ConflictWarning] = []

    # Group constraints by teacher
    teacher_constraints: dict[str, list[Constraint]] = {}
    for c in verified:
        fr = c.formal_representation
        if not fr or not isinstance(fr, dict):
            continue
        teacher = fr.get("teacher")
        if not teacher:
            continue
        teacher_constraints.setdefault(teacher, []).append(c)

    # For each teacher with multiple constraints, check for day+slot overlaps
    for teacher, constraints in teacher_constraints.items():
        if len(constraints) < 2:
            continue
        # Build a map of (day, slot) -> constraint for this teacher
        slot_map: dict[tuple[str, int], Constraint] = {}
        for c in constraints:
            fr = c.formal_representation
            days = fr.get("days") or []
            slots = fr.get("time_slots") or []
            if not days or not slots:
                continue
            for day in days:
                for slot in slots:
                    if (day, slot) in slot_map:
                        other = slot_map[(day, slot)]
                        msg = MESSAGES["conflict_teacher_double_booking"].format(
                            teacher=teacher, day=day, slot=slot,
                        )
                        warnings.append(ConflictWarning(
                            conflict_type="teacher_double_booking",
                            message=msg,
                            constraint_descriptions=[
                                other.formal_representation["description"],
                                fr["description"],
                            ],
                        ))
                    else:
                        slot_map[(day, slot)] = c
    return warnings
```

### Detection Algorithm — Hour-Total Mismatch

```python
def _detect_hour_total_mismatches(
    self,
    verified: list[Constraint],
    timetable: Timetable,
) -> list[ConflictWarning]:
    """Check if total subject hours in constraints exceed timetable weekly_hours."""
    warnings: list[ConflictWarning] = []

    # Count allocated time_slots per constraint
    total_allocated_slots = 0
    slot_constraints: list[str] = []
    for c in verified:
        fr = c.formal_representation
        if not fr or not isinstance(fr, dict):
            continue
        days = fr.get("days") or []
        slots = fr.get("time_slots") or []
        if days and slots:
            allocated = len(days) * len(slots)
            total_allocated_slots += allocated
            desc = fr.get("description", "")
            if desc:
                slot_constraints.append(desc)

    if total_allocated_slots > timetable.weekly_hours:
        msg = MESSAGES["conflict_hour_total_mismatch"].format(
            total=total_allocated_slots,
            weekly_hours=timetable.weekly_hours,
        )
        warnings.append(ConflictWarning(
            conflict_type="hour_total_mismatch",
            message=msg,
            constraint_descriptions=slot_constraints,
        ))

    return warnings
```

### Service Method — `detect_conflicts`

```python
def detect_conflicts(
    self,
    constraints: list[Constraint],
    timetable: Timetable,
) -> list[ConflictWarning]:
    """Detect obvious conflicts among verified constraints before solving."""
    verified = [
        c for c in constraints
        if c.status == "verified" and c.formal_representation
    ]
    if not verified:
        return []

    warnings: list[ConflictWarning] = []
    warnings.extend(self._detect_teacher_double_bookings(verified))
    warnings.extend(self._detect_hour_total_mismatches(verified, timetable))
    return warnings
```

**Key decisions:**
- **Synchronous method** — no DB access, no async needed. Operates on in-memory constraint list already fetched by the controller.
- **Filters to verified only** — pending, translated, rejected, and failed constraints are ignored.
- **Skips None/malformed formal_representation** — defensive coding, logs warning via structlog.
- **Returns list of ConflictWarning** — empty list means no conflicts.

### Controller Integration

```python
# In list_constraints (GET /vincoli):
constraints = await constraint_service.list_constraints(timetable_id=timetable_id)
conflict_warnings = constraint_service.detect_conflicts(constraints, timetable)
# Pass to template: conflict_warnings=conflict_warnings

# In show_verification (GET /verifica):
constraints = await constraint_service.list_constraints(timetable_id=timetable_id)
conflict_warnings = constraint_service.detect_conflicts(constraints, timetable)
# Pass to template: conflict_warnings=conflict_warnings
```

**No new routes needed.** Conflict detection piggybacks on existing GET routes.

### Template — Warning Alert

```html
{% if conflict_warnings %}
<div class="alert warning" role="alert">
  <p><strong>Attenzione: conflitti rilevati tra i vincoli</strong></p>
  {% for warning in conflict_warnings %}
  <p>{{ warning.message }}</p>
  <ul>
    {% for desc in warning.constraint_descriptions %}
    <li>{{ desc }}</li>
    {% endfor %}
  </ul>
  {% endfor %}
</div>
{% endif %}
```

Uses Oat UI alert component with warning variant. Placed above the constraints list / constraint cards.

### Architecture Compliance

**Boundary Rules — MUST follow:**

| Rule | This Story's Application |
|---|---|
| Controller -> Service -> Repository (one-way) | Controller calls `constraint_service.detect_conflicts()`. No new repository methods needed. |
| Controllers handle HTTP only — no business logic | Detection logic lives entirely in ConstraintService. Controller only passes results to template. |
| Guards enforce authorization declaratively | No new guards needed — existing ownership checks on GET routes sufficient. |
| Italian user-facing text, English code/logs | Warning messages in Italian via i18n/errors.py. Python identifiers and log messages in English. |
| `structlog` for all logging, never `print()` | Log skipped constraints (malformed formal_representation) as warnings. |
| Use Litestar DI, never manual instantiation | ConstraintService already wired via DI. No new DI changes needed. |
| `snake_case` for Python/JSON, `kebab-case` for URLs | No new URLs. Python: `detect_conflicts`, `conflict_warnings`, `ConflictWarning`. |
| `jj` for VCS, never raw `git` | All commits via `jj commit -m "message"`. |

**Anti-Patterns — NEVER do:**

- Do NOT implement Z3 solving — that is Story 4.1
- Do NOT implement the generation endpoint — that is Story 4.1
- Do NOT add `from __future__ import annotations` — Python 3.14+
- Do NOT use bare `except:` or catch `Exception` without re-raising
- Do NOT use `git` commands — use `jj` exclusively
- Do NOT persist conflict warnings to DB — they are computed on the fly
- Do NOT block generation when conflicts exist — warnings are advisory only

### Library & Framework Requirements

**Litestar (>=2.21.0) — No new APIs needed for this story.**

Existing APIs already in use:
| API | Usage | Import |
|---|---|---|
| `Request.user.id` | Ownership check (existing) | `from litestar import Request` |
| `Template` | Render with conflict_warnings context | `from litestar.response import Template` |

**No new dependencies.** This story uses only Python stdlib (`dataclasses`) and existing project code.

### File Structure Requirements

**Files to CREATE:**

```
(none — no new files needed)
```

**Files to UPDATE:**

```
easyorario/i18n/errors.py                        (UPDATE: add 2 conflict warning messages)
easyorario/services/constraint.py                (UPDATE: add ConflictWarning dataclass, detect_conflicts method with private helpers)
easyorario/controllers/constraint.py             (UPDATE: call detect_conflicts in list_constraints and show_verification, pass to template)
templates/pages/timetable_constraints.html       (UPDATE: add conflict warning alert section)
templates/pages/timetable_verification.html      (UPDATE: add conflict warning alert section)
tests/services/test_constraint.py                (UPDATE: add conflict detection service tests)
tests/controllers/test_constraint.py             (UPDATE: add conflict warning display controller tests)
```

**Files NOT to touch:**

```
easyorario/models/*                              (NO CHANGE — no schema changes)
easyorario/repositories/*                        (NO CHANGE — no new queries)
easyorario/app.py                                (NO CHANGE — no DI changes)
easyorario/guards/auth.py                        (NO CHANGE)
easyorario/exceptions.py                         (NO CHANGE — conflicts are warnings, not exceptions)
easyorario/services/llm.py                       (NO CHANGE)
easyorario/controllers/auth.py                   (NO CHANGE)
easyorario/controllers/dashboard.py              (NO CHANGE)
easyorario/controllers/timetable.py              (NO CHANGE)
easyorario/controllers/settings.py               (NO CHANGE)
templates/base.html                              (NO CHANGE)
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
- `db_session`, `db_user`, `db_timetable` — for service/repo tests

For conflict detection service tests, create Constraint objects directly in the DB with `status="verified"` and specific `formal_representation` dicts.

**Required Test Cases:**

| Test File | Test Name | Verifies |
|---|---|---|
| **test_constraint.py** (service) | `test_detect_conflicts_finds_teacher_double_booking` | Two verified constraints same teacher, same day+slot → warning |
| **test_constraint.py** (service) | `test_detect_conflicts_finds_hour_total_mismatch` | Total allocated slots exceed weekly_hours → warning |
| **test_constraint.py** (service) | `test_detect_conflicts_returns_empty_for_no_conflicts` | Non-overlapping constraints → empty list |
| **test_constraint.py** (service) | `test_detect_conflicts_skips_non_verified_constraints` | Pending/rejected/translated constraints ignored |
| **test_constraint.py** (service) | `test_detect_conflicts_skips_none_formal_representation` | Constraint with None formal_representation → skipped, no crash |
| **test_constraint.py** (service) | `test_detect_conflicts_empty_constraints_returns_empty` | Empty list → empty list |
| **test_constraint.py** (service) | `test_detect_conflicts_no_overlap_different_days` | Same teacher, different days → no conflict |
| **test_constraint.py** (service) | `test_detect_conflicts_no_overlap_different_slots` | Same teacher, same day, different slots → no conflict |
| **test_constraint.py** (controller) | `test_constraints_page_shows_conflict_warning` | GET /vincoli renders warning alert when conflicts exist |
| **test_constraint.py** (controller) | `test_constraints_page_no_warning_when_no_conflicts` | GET /vincoli no alert when no conflicts |
| **test_constraint.py** (controller) | `test_verification_page_shows_conflict_warning` | GET /verifica renders warning alert when conflicts exist |

**Service Test Setup Pattern:**

```python
async def _create_verified_constraint(
    db_session: AsyncSession,
    timetable_id: uuid.UUID,
    formal_representation: dict,
) -> Constraint:
    """Helper: create a verified constraint with given formal_representation."""
    constraint = Constraint(
        timetable_id=timetable_id,
        natural_language_text="Test constraint",
        formal_representation=formal_representation,
        status="verified",
    )
    db_session.add(constraint)
    await db_session.flush()
    return constraint
```

### Previous Story Intelligence

**From Story 3.3 (Constraint Verification & Approval) — direct predecessor:**

- **177 tests currently passing**: Story 3.4 should add ~11 tests, expected total ~188
- **Template patterns established**: Oat UI alert components used for flash messages. Constraint cards show formal_representation.description. Badge classes use `class="success"`, `class="warning"`, `class="error"` (fixed in latest commit from `data-variant` to class syntax).
- **`formal_representation.description`** is accessible in templates and guaranteed to be a string when formal_representation is not None
- **PRG pattern**: GET routes render templates directly — conflict warnings are computed on each GET request, keeping them always up-to-date
- **`list_constraints()` already returns all constraints**: No need for a separate query — filter to verified in the detect method
- **Ownership check**: Already present on all constraint routes via `timetable.owner_id != request.user.id`
- **`autocommit_handler_maker(commit_on_redirect=True)`**: Not relevant for this story since conflict detection runs on GET routes (no state changes)

### Git Intelligence

**Recent commits (Story 3.3):**
```
5d5e878 fix badge colors: use Oat UI class syntax instead of data-variant attributes
f3d90f2 story 3.3: code review fixes -- redundant template var, null guard, reject ownership test, logging, dead code
fa1e0ba story 3.3: finalize -- update story and sprint status to review
529b7d9 story 3.3: approve/reject routes, template updates with buttons and genera link (tasks 3-5)
92849f9 story 3.3: add i18n messages, verify_constraint and reject_constraint in ConstraintService (tasks 1-2)
```

**Commit patterns to follow:**
- Atomic commits per task group: `story 3.4: description (tasks N-M)`
- `just check` before every commit (format + lint + typecheck)
- `just test` separately to verify tests pass
- Create bookmark: `jj bookmark create story-3.4-pre-solve-conflict-detection`

**Suggested commit sequence for Story 3.4:**
1. `story 3.4: add i18n conflict messages (task 2)`
2. `story 3.4: add ConflictWarning dataclass and detect_conflicts in ConstraintService (task 1)`
3. `story 3.4: integrate conflict detection into controller routes (task 3)`
4. `story 3.4: update templates with conflict warning alerts (task 4)`
5. `story 3.4: tests for conflict detection service and controller (task 5)`

### Project Structure Notes

- **Flat layout confirmed:** `easyorario/` at project root (no `src/`). Follow what exists, not the architecture doc.
- **Tests at `tests/`** at project root, mirroring `easyorario/` structure.
- **Templates at `templates/`** at project root, pages under `templates/pages/`.
- **No new files or directories needed** — all changes are to existing files.
- **No database migrations needed** — no schema changes.
- **ConflictWarning dataclass** goes in `services/constraint.py` alongside the service (not a separate file — it's a value object, not a model).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.4]
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 3 overview]
- [Source: _bmad-output/planning-artifacts/epics.md#FR-3: Constraint Conflict Detection]
- [Source: _bmad-output/planning-artifacts/architecture.md#Core Architectural Decisions — Controller->Service->Repository]
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns & Consistency Rules]
- [Source: _bmad-output/planning-artifacts/architecture.md#Error Handling Pattern]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Constraint Verification]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Key Interaction Patterns]
- [Source: _bmad-output/implementation-artifacts/3-3-constraint-verification-approval.md — all sections]
- [Source: easyorario/controllers/constraint.py — existing ConstraintController with list/add/translate/show_verification/approve/reject routes]
- [Source: easyorario/services/constraint.py — existing ConstraintService with add, list, verify, reject, translate methods]
- [Source: easyorario/services/llm.py — ConstraintTranslation Pydantic model defining formal_representation JSON schema]
- [Source: easyorario/models/constraint.py — Constraint model with formal_representation, status fields]
- [Source: easyorario/models/timetable.py — Timetable model with weekly_hours, subjects, teachers fields]
- [Source: easyorario/repositories/constraint.py — ConstraintRepository with get_by_timetable]
- [Source: easyorario/exceptions.py — exception hierarchy]
- [Source: easyorario/i18n/errors.py — Italian message mappings]
- [Source: easyorario/guards/auth.py — requires_responsible_professor guard]
- [Source: templates/pages/timetable_constraints.html — constraint list page]
- [Source: templates/pages/timetable_verification.html — verification page with constraint cards]
- [Source: tests/services/test_constraint.py — existing constraint service tests]
- [Source: tests/controllers/test_constraint.py — existing constraint controller tests]
- [Source: tests/conftest.py — test fixtures and helpers]
- [Source: CLAUDE.md#Architecture]
- [Source: CLAUDE.md#Commands]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

No blocking issues encountered.

### Completion Notes List

- Implemented `ConflictWarning` dataclass in `services/constraint.py` as a simple value object (not persisted)
- Added `detect_conflicts()` synchronous method on `ConstraintService` with two private helpers: `_detect_teacher_double_bookings()` and `_detect_hour_total_mismatches()`
- Detection filters to verified constraints only and skips None/malformed `formal_representation` with structlog warning
- Added 2 Italian i18n messages: `conflict_teacher_double_booking`, `conflict_hour_total_mismatch`
- Controller integration: all 3 code paths that render constraint templates (GET /vincoli, GET /verifica, POST /verifica) now pass `conflict_warnings` to template context
- Template alert uses Oat UI `alert warning` class, positioned above constraints list/cards
- 11 new tests added (8 service + 3 controller), total test count: 177 → 188, all passing
- TDD approach followed: wrote failing tests first, then minimal implementation
- Pyright fix: added `not fr` guard in inner loop and `or {}` pattern for optional dict access

### Change Log

- 2026-02-23: Story 3.4 implementation complete — pre-solve conflict detection for teacher double-bookings and hour-total mismatches

### File List

- `easyorario/services/constraint.py` (UPDATED: added ConflictWarning dataclass, detect_conflicts method with private helpers)
- `easyorario/i18n/errors.py` (UPDATED: added 2 conflict warning messages)
- `easyorario/controllers/constraint.py` (UPDATED: call detect_conflicts in list_constraints, show_verification, translate_constraints, and add_constraint error path)
- `templates/pages/timetable_constraints.html` (UPDATED: added conflict warning alert section)
- `templates/pages/timetable_verification.html` (UPDATED: added conflict warning alert section)
- `tests/services/test_constraint.py` (UPDATED: added 8 conflict detection service tests)
- `tests/controllers/test_constraint.py` (UPDATED: added 3 conflict warning display controller tests)
