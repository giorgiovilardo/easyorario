# Easyorario

An Italian school timetable generator where professors write scheduling constraints in natural language, an LLM translates them to formal representations, and a Z3 solver produces valid timetables.

Also an experiment in AI-assisted software development -- from PRD to working code in 4 days using BMAD methodology and Claude Code.

## How It Works

1. A Responsible Professor creates a timetable and configures an LLM endpoint
2. They write constraints in plain Italian (e.g. "Il prof. Rossi non è disponibile il mercoledì")
3. The system translates each constraint to a formal representation via LLM
4. The professor verifies and approves translated constraints
5. A Z3 solver generates a valid timetable satisfying all constraints

## AI Integration Log

AI is involved in this project at two levels: it built the application and it runs inside it.

### AI as Builder: BMAD + Claude Code

The entire project was planned and implemented using an AI-assisted workflow. A human wrote the PRD; everything after that was produced by AI agents, with human review at each stage.

**The BMAD pipeline** (an AI-assisted software development methodology) generated the architecture, UX specification, epic breakdown, sprint plan, and implementation stories from the PRD. Each BMAD phase was run as a separate AI agent conversation with a specialized system prompt (Architect, UX Designer, Product Owner, Scrum Master).

**Claude Code** (Claude as a coding agent) implemented every story using strict TDD (red-green-refactor). Each story was implemented in a fresh conversation, following the tasks defined by the BMAD Story Creator agent. After implementation, a separate code review conversation (different model, fresh context) caught issues that were then fixed.

The human role throughout was: write the PRD, trigger each BMAD phase, review outputs, start Claude Code sessions, and review code review findings.

#### Timeline

| Date | What | Commits | Tests |
|------|------|---------|-------|
| Feb 16 | Human writes PRD (428 lines) | 1 | -- |
| Feb 17 AM | BMAD phases 1-6: architecture, UX, epics, IR, sprint plan, stories | 6 | -- |
| Feb 17 | Stories 1.1-1.4: project skeleton, user registration, login/sessions, RBAC dashboard | 41 | ~80 |
| Feb 17-18 | Stories 2.1-2.2: timetable CRUD, constraint input | 15 | ~130 |
| Feb 18-19 | Story 3.1: LLM endpoint configuration and connectivity test | 4 | ~145 |
| Feb 19-20 | Story 3.2: constraint translation via LLM | 7 | 161 |

**Totals:** 82 commits, 161 tests, 1,458 lines of application code, 2,584 lines of test code, 11 templates, 30 Python modules -- produced across 4 working days.

#### What Worked

- **BMAD stories were implementable as-is.** Task breakdowns were specific enough that Claude Code could follow them without ambiguity. Each story included acceptance criteria, task/subtask lists, and dev notes with code snippets.
- **TDD kept the agent honest.** Requiring tests before implementation meant the agent could not skip edge cases or produce code that looked right but didn't work.
- **Separate code review conversations caught real issues.** Session fixation vulnerabilities, missing structlog usage, unnecessary imports, redundant guards -- things the implementing agent had normalized.
- **jj (Jujutsu) made atomic commits painless.** No staging area friction. Every meaningful step became a commit naturally.

#### What Didn't Work (or Needed Human Intervention)

- **BMAD agents hallucinated library APIs.** The architecture specified bcrypt; Argon2 was substituted during implementation after checking actual Python ecosystem support.
- **Test isolation bugs.** In-memory SQLite with SQLAlchemy async required specific pool configuration (`StaticPool`) that the agent didn't know about initially -- the human debugged this.
- **The agent needed explicit memory.** Patterns discovered during debugging (e.g., `retrieve_user_handler` cannot open its own DB session with `StaticPool`) had to be written into CLAUDE.md and memory files to persist across conversations.

### AI in the Product: LLM Constraint Translation

The application itself uses an LLM at runtime to translate natural language Italian constraints into structured JSON:

- **Single contact point:** `easyorario/services/llm.py` handles all LLM communication
- **OpenAI-compatible API** with Structured Outputs (JSON Schema response format)
- **Pydantic validation** of every LLM response via `ConstraintTranslation` model
- **6 constraint types:** `teacher_unavailable`, `teacher_preferred`, `subject_scheduling`, `max_consecutive`, `room_requirement`, `general`
- **Session-based API keys** -- never persisted to the database, provided per session by the user
- **Error handling:** fail-fast on auth errors, graceful partial failure (some constraints can fail while others succeed), retry mechanism for failed translations

The system prompt provides full timetable context (class, subjects, teachers, time slots) and instructs the model to output structured JSON. The model is treated as an unreliable external service -- every response is validated, and failures are surfaced to the user in Italian with actionable next steps.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.14 |
| Web framework | Litestar (ASGI, server-rendered) |
| Templates | Jinja2 + Oat UI (semantic CSS) |
| Database | SQLite (WAL) via aiosqlite + SQLAlchemy async |
| ORM pattern | Advanced Alchemy (repository pattern) |
| Solver | Z3 Theorem Prover |
| Auth | Argon2 + session-based (DB-backed cookies) |
| LLM integration | httpx + Pydantic (OpenAI-compatible API) |
| VCS | jj (Jujutsu), colocated with git |
| Migrations | Alembic (batch mode for SQLite) |
| Logging | structlog (JSON) |

## Project Status

Proof-of-concept, desktop-only. Epics 1-3 (auth, timetable/constraint CRUD, LLM translation) are implemented with 161 tests. Epics 4-5 (Z3 solving, collaboration, sharing) are planned but not yet built.

## Experimental Tools

Beyond the AI workflow, the project experiments with:

- **jj (Jujutsu)** -- a next-generation VCS where the working copy is always a commit and there is no staging area. Used for all 82 atomic commits.
- **Oat UI** (oat.ink) -- a minimalist semantic CSS framework (8KB). No classes, no build step. HTML elements are styled by their semantics.
- **Oatsmith** -- a Claude Code skill for crafting and reviewing Oat UI templates.
