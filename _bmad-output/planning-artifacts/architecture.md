---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
lastStep: 8
status: 'complete'
completedAt: '2026-02-16'
inputDocuments:
  - 'docs/PRD.md'
workflowType: 'architecture'
project_name: 'easyorario'
user_name: 'MasterArchitect'
date: '2026-02-16'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**

16 FRs across 5 categories. The architecture must support two distinct processing pipelines: (1) an NLP pipeline where natural language Italian text is translated via LLM into formal constraint representations, verified by the user, and fed to a solver; and (2) a collaborative review pipeline where timetable drafts flow through revision cycles with comments and notifications. The constraint input/translation/verification loop (FR-1 through FR-3) is the most architecturally novel component. Timetable generation (FR-5 through FR-7) requires a constraint solver with timeout handling and conflict explanation. The sharing and lifecycle features (FR-8 through FR-16) are standard CRUD/workflow patterns with role-based access layered on top.

**Non-Functional Requirements:**

16 NFRs with the most architecturally significant being:
- **Performance:** 5-minute solve ceiling (NFR-1), 3-second page loads on 4G (NFR-2), 10-second LLM translation P95 (NFR-3) — the solver and LLM calls are long-running async operations that cannot block the request cycle.
- **Security:** Password hashing with bcrypt/Argon2 (NFR-5), per-request authorization (NFR-6), AES-256 encryption for API keys at rest (NFR-7), GDPR data export/deletion (NFR-8).
- **Usability:** Mobile-responsive timetable grid from 360px to 1920px (NFR-9), full Italian UI (NFR-10).
- **Reliability:** 95% uptime during peak Aug-Sep window (NFR-12), zero data loss on normal shutdown (NFR-13).

**Scale & Complexity:**

- Primary domain: Full-stack web application
- Complexity level: Medium
- Estimated architectural components: 6-8 major components (auth, constraint input UI, LLM translation service, constraint solver, timetable renderer, comment/notification system, sharing/access control, data persistence)

### Technical Constraints & Dependencies

- **External LLM dependency:** User-configurable OpenAI-compatible endpoint; architecture must handle variable latency, rate limits, and unavailability gracefully with retry logic and potential manual fallback.
- **Constraint solver:** Must support Italian school domain rules (6-day week, subject types, teacher availability patterns, resource conflicts). Solve operations are computationally intensive and long-running relative to typical web requests.
- **Single-class MVP scope:** Architecture should be designed for single-class but not preclude future multi-class coordination (Growth Phase).
- **No mobile native apps:** Web-only with responsive design; no native platform dependencies.
- **Italian-only localization:** MVP is monolingual but Growth Phase mentions multi-language; architecture should not hardcode Italian strings.

### Cross-Cutting Concerns Identified

- **Authentication & Authorization:** Every API endpoint must enforce RBAC (Responsible Professor / Professor / Public). Draft vs. final access rules create a content-level permission model.
- **Async Operation Management:** Both LLM translation and constraint solving are long-running; need async job processing, progress feedback (SSE), and timeout handling.
- **Error Handling in Italian:** All user-facing errors must be localized; LLM failures, solver timeouts, and constraint conflicts all need human-readable Italian explanations.
- **API Key Security:** LLM API keys are user-provided secrets requiring encryption at rest and careful handling to prevent logging/exposure.
- **Responsive Timetable Rendering:** The week-grid (6 columns x 6-8 rows) must be readable on 360px mobile screens — the primary UI/UX challenge.
- **Revision Management:** Timetables have a versioned lifecycle (draft revisions -> final) with immutability after finalization; comments are tied to specific revisions and timeslots.
- **Architectural Decision Implications:** Four key decisions shape the architecture: (1) LLM integration requires an orchestrated pipeline with pre/post-processing for testability and graceful error handling; (2) Constraint solving requires async job processing with progress feedback; (3) Revision data model should favor simplicity (snapshots over event sourcing) given small data volumes; (4) Notification model should match user behavior (async email + in-app polling, not real-time push).

## Starter Template Evaluation

### Primary Technology Domain

Server-rendered Python web application. No SPA, no Node.js toolchain. Jinja2 templates served by Litestar with semantic CSS via Oat UI.

### Technical Preferences Established

The user has pre-selected the entire stack. No starter template CLI applies — this is a custom Python project with dependencies already declared in `pyproject.toml`.

### Stack Decisions (User-Specified)

**Language & Runtime:**
- Python >=3.14 with type checking via Pyright
- Linting/formatting via Ruff

**Backend Framework:**
- Litestar >=2.21.0 — ASGI framework with built-in Jinja2 template support, dependency injection, and OpenAPI generation

**Frontend/Templating:**
- Jinja2 server-rendered templates (included in Litestar's template engine support)
- Minimal JavaScript — only where strictly necessary (e.g., Oat UI web components for tabs/dropdowns)

**CSS Framework:**
- Oat UI (oat.ink) — ultra-lightweight (~8KB), zero-dependency, semantic HTML-first CSS library
- Styles native HTML elements directly via semantic attributes — no class soup
- Built-in dark theme, 12-column grid, ARIA/accessibility support
- Web Components for complex interactions (tabs, dropdowns, dialogs)

**Database:**
- SQLite via aiosqlite + SQLAlchemy async (Advanced Alchemy / litestar[sqlalchemy])
- Sufficient for demo/MVP scale (10 concurrent users, small data volumes)

**Constraint Solver:**
- Z3 Theorem Prover >=4.15.8.0 — Python bindings for constraint satisfaction
- Models timetable rules as Z3 constraints, solver finds valid assignments

**Testing:**
- pytest + pytest-asyncio for async test support
- ipdb/ipython for interactive debugging

**Task Runner:**
- just command runner for project commands (dev server, tests, linting, Docker builds, database migrations, etc.)
- Single justfile at project root as the canonical entry point for all project operations

**Deployment:**
- Docker containerized
- Target: single VPS
- No cloud-specific services or serverless dependencies

### Starter Options Considered

No external starter template applies. The project already has:
- pyproject.toml with core dependencies declared
- .venv with Python 3.14
- Ruff, Pyright, pytest in dev dependencies

The "starter" is the project structure itself, which will be defined in the architectural decisions phase.

**Note:** Project scaffolding (directory structure, justfile, Docker setup, Litestar app initialization) should be the first implementation story.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- Data model with separate Constraint table and individual verification flow
- Session-based auth with Argon2 password hashing
- Litestar background tasks for Z3 solving (sync function, auto-threaded)
- LLM API keys not persisted — provided per session

**Important Decisions (Shape Architecture):**
- Controller-per-domain route organization
- Alembic migrations
- Italian error templates with English server-side structured logging
- Vanilla JS polling for async operations
- Desktop-only PoC

**Deferred Decisions (Post-MVP):**
- Caching (not needed at this scale)
- Mobile/responsive layout
- SSE or WebSocket for real-time updates
- Reverse proxy / HTTPS (Caddy setup on hardware later)
- Monitoring/alerting infrastructure

### Data Architecture

- **ORM:** Advanced Alchemy (Litestar's SQLAlchemy integration) with repository pattern
- **Migrations:** Alembic for schema versioning
- **SQLite WAL mode:** Database configured with `PRAGMA journal_mode=WAL` at connection time for concurrent read access during writes
- **Caching:** None. SQLite reads are fast enough for 10 concurrent users.
- **Core Entities:**
  - **User** — email, hashed password (Argon2), role (responsible_professor / professor)
  - **Timetable** — class identifier, status (draft/final), owner FK
  - **Revision** — timetable FK, revision number, generated grid data (JSON column), constraints snapshot
  - **Constraint** — timetable FK, natural language text, formal Z3 representation (JSON), status (pending/verified/rejected)
  - **Comment** — revision FK, author FK, timeslot reference, text, timestamp
- **Grid storage:** Timetable grid stored as JSON on Revision (6 days x ~8 slots = small payload)

### Authentication & Security

- **Authentication:** Session-based with DB-backed cookie sessions (Litestar built-in session middleware)
- **Password hashing:** Argon2 via `argon2-cffi`
- **LLM API keys:** Not stored. User provides per session. No encryption complexity.
- **CSRF:** Litestar built-in CSRF middleware on all form endpoints
- **Authorization:** Role-based — Responsible Professor (full access), Professor (read + comment), Public (final timetable view only). Enforced per-request via Litestar guards.

### API & Communication Patterns

- **Route organization:** Controller classes per domain — AuthController, TimetableController, ConstraintController, SolverController, CommentController, SettingsController
- **Async operations:** Litestar background tasks. Z3 solver written as sync function, automatically wrapped to thread pool via Litestar's `AsyncCallable`. Job status stored in DB, frontend polls for completion.
- **Error handling:** Litestar exception handlers render Italian error templates for user-facing errors. Structured logging server-side via `structlog`. Error message mapping for common failures (LLM timeout, solver timeout, unsolvable constraints, auth failures).

### Frontend Architecture

- **Templating:** Jinja2 with standard inheritance — base layout, page templates, partial fragments
- **CSS:** Oat UI included via static CSS/JS files. Custom CSS only for timetable grid table styling.
- **JavaScript:** Minimal. Vanilla JS `fetch()` polling on generation page for async solver status. No framework, no build step.
- **Timetable display:** HTML `<table>` element, desktop only.
- **Mobile:** Out of scope for PoC.

### Infrastructure & Deployment

- **Container:** Single Dockerfile. Litestar app serving directly.
- **Database volume:** SQLite file on Docker mounted volume for persistence across container restarts.
- **Reverse proxy:** Deferred. User will set up Caddy on hardware if needed.
- **Logging:** `structlog` for structured JSON logging to stdout. Access via `docker logs`.
- **Environment config:** `.env` file with `SECRET_KEY`, `DATABASE_URL`.
- **CI/CD:** Not defined for PoC.

### Decision Impact Analysis

**Implementation Sequence:**
1. Project scaffolding (directory structure, justfile, Dockerfile)
2. Database models + Alembic setup
3. Auth system (session middleware, Argon2, registration/login)
4. Timetable CRUD + revision management
5. Constraint input + LLM translation pipeline
6. Z3 solver integration + background task execution
7. Comment system
8. Sharing (public links for finalized timetables)

**Cross-Component Dependencies:**
- Constraint verification flow drives both the data model (status field) and the UI (step-by-step verification interface)
- Background task system is shared between LLM translation and Z3 solving
- Session-based auth means LLM API key is available in session data for the constraint translation pipeline

## Implementation Patterns & Consistency Rules

### Naming Patterns

**Database Naming:**
- Tables: `snake_case`, plural (`users`, `timetables`, `constraints`, `revisions`, `comments`)
- Columns: `snake_case` (`created_at`, `timetable_id`, `natural_language_text`)
- Foreign keys: `{referenced_table_singular}_id` (`user_id`, `timetable_id`, `revision_id`)
- Indexes: `ix_{table}_{column}` (`ix_constraints_timetable_id`)

**Python Code:**
- PEP 8 throughout: `snake_case` for functions, variables, modules; `PascalCase` for classes
- Files/modules: `snake_case` (`timetable_controller.py`, `constraint_service.py`)
- Constants: `UPPER_SNAKE_CASE`

**Routes:**
- URL paths: `kebab-case` (`/timetables/{timetable_id}/constraints`, `/solver/check-status`)
- Path parameters: `snake_case` in Python, rendered as-is in URL (`{timetable_id}`)

**JSON Fields (polling endpoints):**
- `snake_case` to match Python conventions. No camelCase translation layer.

### Structure Patterns

**Project Organization:** Layer-based, matching Litestar conventions.
- `controllers/`, `services/`, `models/`, `templates/`

**Test Organization:**
- `tests/` directory at project root mirroring `src/` structure
- e.g., `src/easyorario/controllers/timetable.py` → `tests/controllers/test_timetable.py`

**Templates:**
- `templates/` directory with: `base.html`, `pages/`, `partials/`
- `static/` directory with: `css/`, `js/` (Oat UI files + custom styles)

### Format Patterns

**JSON Response Format (for polling/async endpoints):**

```json
{"status": "pending", "data": null, "error": null}
{"status": "completed", "data": {"revision_id": 42}, "error": null}
{"status": "failed", "data": null, "error": {"code": "unsolvable", "message": "I vincoli sono in conflitto..."}}
```

Consistent wrapper with `status`, `data`, `error`. Three possible statuses for async jobs: `pending`, `completed`, `failed`.

**Date/Time in JSON:** ISO 8601 strings (`"2026-09-15T08:30:00"`)

### Process Patterns

**TDD Workflow (Kent Beck's Tidy First):**

All AI agents MUST follow this cycle:

1. **Red:** Write a small, focused test that fails. One behavior per test. Test names describe the behavior in `test_{action}_{condition}_{expected_result}` format (e.g., `test_create_timetable_with_valid_input_returns_draft`).
2. **Green:** Write the minimum code to make the test pass. No extra logic, no premature abstractions.
3. **Refactor/Tidy:** Clean up only if needed — extract duplication, rename for clarity, simplify. All tests must stay green.
4. **Repeat.**

**TDD Rules:**
- Never write production code without a failing test first
- Never write more than one failing test at a time
- Tidy steps are optional — only when the code asks for it
- Commit after each green-refactor cycle when the change is meaningful

**Version Control:**
- `jj` (Jujutsu) as the primary VCS. Git is the backend only.
- AI agents must use `jj` commands, never `git` directly.
- Commit workflow: `jj new`, `jj describe`, `jj commit` — not `git add/commit`.

**Error Handling Pattern:**
- Custom exception classes inheriting from a base `EasyorarioError`
- Domain-specific exceptions: `UnsolvableConstraintsError`, `LLMTranslationError`, `ConstraintConflictError`
- Litestar exception handlers map these to Italian error templates
- `structlog` logs the full exception server-side

**Loading/Async Status Pattern:**
- Background jobs write status to a `Job` table (or status field on the entity) — `pending`, `running`, `completed`, `failed`
- Frontend polls `GET /solver/status/{job_id}` every 3 seconds
- Timeout after 5 minutes, show Italian timeout message

### Enforcement Guidelines

**All AI Agents MUST:**
- Follow the TDD red-green-refactor cycle for every feature
- Use `snake_case` for all Python code and JSON fields
- Use `kebab-case` for URL paths
- Place tests in `tests/` mirroring `src/` structure
- Write user-facing text in Italian, logs and code in English
- Use `structlog` for all logging, never `print()`
- Use Litestar's dependency injection, never manual instantiation of services
- Use `jj` for all version control operations, never raw `git` commands

**Anti-Patterns (NEVER do):**
- Write production code before the test
- Use `camelCase` in Python code or JSON
- Put test files next to source files
- Hardcode Italian strings in Python code (use templates or message mappings)
- Use bare `except:` or catch `Exception` without re-raising
- Log LLM API keys or session secrets
- Use `git add`, `git commit`, or any direct git commands (use `jj` exclusively)

## Project Structure & Boundaries

### Complete Project Directory Structure

```
easyorario/
├── pyproject.toml
├── justfile
├── Dockerfile
├── .env.example
├── .gitignore
├── alembic.ini
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── src/
│   └── easyorario/
│       ├── __init__.py
│       ├── app.py                    # Litestar app factory, plugin registration
│       ├── config.py                 # Settings from env vars
│       ├── exceptions.py             # EasyorarioError base + domain exceptions
│       ├── controllers/
│       │   ├── __init__.py
│       │   ├── auth.py               # Login, register, logout
│       │   ├── timetable.py          # CRUD, finalization, sharing
│       │   ├── constraint.py         # Input, verification, management
│       │   ├── solver.py             # Trigger generation, poll status
│       │   ├── comment.py            # Add/list comments
│       │   └── settings.py           # LLM endpoint config (session)
│       ├── services/
│       │   ├── __init__.py
│       │   ├── auth.py               # Password hashing, session management
│       │   ├── timetable.py          # Timetable lifecycle logic
│       │   ├── constraint.py         # Constraint CRUD + status transitions
│       │   ├── llm.py                # LLM orchestration pipeline (pre-process, call, validate)
│       │   └── solver.py             # Z3 constraint modeling + solving (sync)
│       ├── models/
│       │   ├── __init__.py
│       │   ├── base.py               # SQLAlchemy base, common mixins
│       │   ├── user.py
│       │   ├── timetable.py
│       │   ├── revision.py
│       │   ├── constraint.py
│       │   └── comment.py
│       ├── repositories/
│       │   ├── __init__.py
│       │   ├── user.py
│       │   ├── timetable.py
│       │   ├── revision.py
│       │   ├── constraint.py
│       │   └── comment.py
│       ├── guards/
│       │   ├── __init__.py
│       │   └── auth.py               # Role-based access guards
│       └── i18n/
│           ├── __init__.py
│           └── errors.py             # Italian error message mappings
├── templates/
│   ├── base.html                     # Layout: nav, Oat UI includes, footer
│   ├── pages/
│   │   ├── index.html
│   │   ├── login.html
│   │   ├── register.html
│   │   ├── dashboard.html            # List timetables
│   │   ├── timetable/
│   │   │   ├── create.html
│   │   │   ├── view.html             # Timetable grid + comments
│   │   │   └── public.html           # Public final view (no auth)
│   │   ├── constraints/
│   │   │   ├── input.html            # NL constraint entry
│   │   │   └── verify.html           # Verification step-by-step
│   │   ├── solver/
│   │   │   └── progress.html         # Generation progress + polling
│   │   └── settings.html             # LLM endpoint config
│   └── partials/
│       ├── timetable_grid.html       # <table> grid component
│       ├── constraint_card.html      # Single constraint display
│       ├── comment_list.html
│       └── flash_messages.html
├── static/
│   ├── css/
│   │   └── app.css                   # Custom styles (grid table)
│   └── js/
│       └── poll.js                   # Solver status polling
├── tests/
│   ├── conftest.py                   # Fixtures: test client, test DB, factories
│   ├── controllers/
│   │   ├── test_auth.py
│   │   ├── test_timetable.py
│   │   ├── test_constraint.py
│   │   ├── test_solver.py
│   │   └── test_comment.py
│   ├── services/
│   │   ├── test_auth.py
│   │   ├── test_timetable.py
│   │   ├── test_constraint.py
│   │   ├── test_llm.py
│   │   └── test_solver.py
│   ├── models/
│   │   └── test_models.py
│   └── repositories/
│       └── test_repositories.py
└── docs/
    └── PRD.md
```

### Architectural Boundaries

**Controller → Service → Repository:**
- Controllers handle HTTP: parse requests, call services, render templates. No business logic.
- Services contain business logic: validation, orchestration, state transitions. No HTTP awareness.
- Repositories handle data access via Advanced Alchemy. No business logic.
- One-way dependency: Controller → Service → Repository. Never reversed.

**LLM Integration Boundary:**
- `services/llm.py` is the sole point of contact with external LLM APIs.
- Accepts raw NL text, returns structured constraint representation.
- All pre-processing (text splitting, prompt construction) and post-processing (schema validation, error handling) lives here.
- Controllers and other services never call the LLM directly.

**Solver Boundary:**
- `services/solver.py` is the sole Z3 interface.
- Accepts verified constraints (from DB), returns timetable grid or conflict explanation.
- Sync function — Litestar background tasks handle threading.
- No HTTP awareness, no DB access. Receives data, returns data.

**Auth Boundary:**
- `guards/auth.py` enforces role-based access on routes.
- `services/auth.py` handles password hashing and session logic.
- Controllers never check permissions directly — guards do it declaratively.

### Requirements to Structure Mapping

| FR Category | Controllers | Services | Models | Templates |
|---|---|---|---|---|
| Constraint Input & Management (FR-1 to FR-4) | `constraint.py` | `constraint.py`, `llm.py` | `constraint.py` | `constraints/` |
| Timetable Generation (FR-5 to FR-7) | `solver.py` | `solver.py` | `revision.py` | `solver/` |
| Visualization & Sharing (FR-8 to FR-10) | `timetable.py`, `comment.py` | `timetable.py` | `timetable.py`, `comment.py` | `timetable/`, `partials/` |
| User & Access (FR-11 to FR-13) | `auth.py`, `settings.py` | `auth.py` | `user.py` | `login.html`, `register.html`, `settings.html` |
| Lifecycle Management (FR-14 to FR-16) | `timetable.py` | `timetable.py` | `timetable.py`, `revision.py` | `timetable/` |

### Data Flow

```
User (browser)
  → Controller (HTTP handling)
    → Service (business logic)
      → Repository (data access) → SQLite
      → LLM Service → External LLM API
      → Solver Service → Z3 (in thread pool)
    → Jinja2 Template (render response)
  → User (browser)
```

**Async flow (solver):**
```
User triggers generation → Controller → Service spawns background task → returns immediately
Background task: Service → Solver → writes result to DB
User polls /solver/status/{id} → Controller → Repository → returns status JSON
```

## Architecture Validation Results

### Coherence Validation

**Decision Compatibility:** All technology choices verified compatible. Python 3.14 + Litestar + SQLAlchemy async + aiosqlite + Z3 + Argon2 + structlog + Alembic + Oat UI — no version conflicts or incompatibilities.

**Pattern Consistency:** Naming conventions (snake_case Python/JSON, kebab-case URLs, PascalCase classes) are internally consistent and match Python/Litestar community standards. Layer-based organization aligns with Litestar controller patterns. TDD workflow is stack-agnostic.

**Structure Alignment:** Controller → Service → Repository layering is fully reflected in the directory structure. Template organization mirrors the controller routing. Test structure mirrors source structure. All boundaries are enforceable through import conventions.

### Requirements Coverage

**Functional Requirements Coverage:**

| FR | Status | Architectural Support |
|---|---|---|
| FR-1 NL Constraint Input | Covered | constraint controller + input template |
| FR-2 Constraint Translation | Covered | llm service + verify template |
| FR-3 Conflict Detection | Covered | solver service pre-solve validation |
| FR-4 Constraint Library | Deferred | COULD priority — post-MVP |
| FR-5 Single-Class Generation | Covered | solver service + background tasks |
| FR-6 Regeneration | Covered | revision model + timetable service |
| FR-7 Unsolvable Handling | Covered | solver returns conflict explanation + Italian error templates |
| FR-8 Week-Grid View | Covered | timetable_grid.html partial |
| FR-9 Sharing via Link | Covered | timetable controller + public.html |
| FR-10 Comment System | Partial | Comments supported; real-time notification deferred |
| FR-11 User Auth | Covered | auth controller + session middleware |
| FR-12 RBAC | Covered | guards/auth.py |
| FR-13 LLM Config | Covered | settings controller, session-based |
| FR-14 Finalization | Covered | timetable controller + service |
| FR-15 Deletion | Covered | timetable controller + service |
| FR-16 Revision History | Covered | revision model |

**Non-Functional Requirements Coverage:**

| NFR | Status | Note |
|---|---|---|
| NFR-1 Generation Latency | Covered | Background tasks + 5min timeout |
| NFR-2 Page Load | Covered | Server-rendered, ~8KB CSS, minimal JS |
| NFR-3 LLM Latency | Covered | LLM service with timeout |
| NFR-4 Concurrent Users | Covered | SQLite WAL + async Litestar |
| NFR-5 Password Hashing | Covered | Argon2 |
| NFR-6 Authorization | Covered | Per-route guards |
| NFR-7 API Key Protection | Exceeded | Keys not stored at all (better than encrypted at rest) |
| NFR-8 Data Privacy | Covered | Minimal PII, no student data |
| NFR-9 Mobile | Deferred | Desktop-only PoC (conscious deviation) |
| NFR-10 Italian UI | Covered | i18n/errors.py + Italian templates |
| NFR-11 Constraint Usability | Covered | NL input, no syntax knowledge needed |
| NFR-12 Availability | Covered | Docker on VPS |
| NFR-13 Data Persistence | Covered | SQLite on mounted volume |
| NFR-14 Error Handling | Covered | Exception handlers + structlog |
| NFR-15 Code Docs | Covered | This architecture document |
| NFR-16 Dependencies | Covered | pyproject.toml with version pins |

### Conscious PoC Deviations from PRD

1. **Mobile responsiveness (NFR-9 MUST):** Deferred to desktop-only. Rationale: PoC validates core workflow; responsive grid is a UI polish task.
2. **API key encryption (NFR-7 MUST):** Keys not stored instead of encrypted. Rationale: no data at rest is more secure than encrypted data at rest.
3. **Comment notifications (FR-10):** No push/email notification. Responsible Professor sees comments on next visit. Rationale: sufficient for PoC with small user count.

### Architecture Completeness Checklist

- [x] Project context thoroughly analyzed
- [x] Scale and complexity assessed
- [x] Technical constraints identified
- [x] Cross-cutting concerns mapped
- [x] Critical decisions documented with versions
- [x] Technology stack fully specified
- [x] Integration patterns defined
- [x] Naming conventions established
- [x] Structure patterns defined
- [x] Process patterns documented (TDD, VCS)
- [x] Complete directory structure defined
- [x] Component boundaries established
- [x] Requirements to structure mapping complete

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION

**Confidence Level:** High

**Key Strengths:**
- Simple, boring technology choices — no overengineering
- Clear separation of concerns (controller/service/repository)
- LLM and solver boundaries are well-isolated and independently testable
- TDD workflow ensures incremental, verifiable progress
- No external infrastructure dependencies beyond the LLM API

**Areas for Future Enhancement:**
- Mobile responsiveness when PoC is validated
- Real-time comment notifications (email or SSE)
- Constraint template library (FR-4)
- Migration to PostgreSQL if SQLite hits concurrency limits
- CI/CD pipeline
