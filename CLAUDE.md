# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Easyorario is a server-rendered Python web app for Italian school timetable generation. Users write scheduling constraints in natural language Italian, an LLM translates them to formal representations, and a Z3 solver generates valid timetables. Desktop-only PoC targeting ~10 concurrent users.

## Tech Stack

- **Python 3.14** with Litestar (ASGI framework), Jinja2 templates, Oat UI (semantic CSS)
- **SQLite** (WAL mode) via aiosqlite + SQLAlchemy async + Advanced Alchemy (repository pattern)
- **Z3 Theorem Prover** for constraint solving, run as sync in Litestar background tasks
- **Argon2** password hashing, session-based auth with DB-backed cookies
- **Alembic** for database migrations (batch mode for SQLite)
- **structlog** for JSON structured logging

## Commands

Package management uses **uv**. Task runner uses **just** (justfile at project root).

```bash
just dev              # Start Litestar dev server with hot reload
just test             # Run pytest
just check            # Run format + lint + typecheck (run before every commit)
just lint             # Run ruff check + pyright
just fmt              # Run ruff format
just db-migrate       # Run alembic upgrade head
just db-revision msg  # Create new alembic migration
just docker-build     # Build Docker image
just docker-run       # Run Docker container
```

Direct commands (if justfile not yet created):
```bash
uv run pytest                          # Run all tests
uv run pytest tests/services/test_auth.py  # Run single test file
uv run pytest -k test_create_timetable     # Run test by name
uv run ruff check easyorario/ tests/       # Lint
uv run ruff format easyorario/ tests/     # Format
uv run pyright easyorario/                # Type check
```

## Architecture

### Layered Architecture (one-way dependencies)

```
Controller (HTTP) → Service (Business Logic) → Repository (Data Access) → SQLite
```

- **Controllers** (`easyorario/controllers/`): HTTP handling, request parsing, template rendering. No business logic.
- **Services** (`easyorario/services/`): Business logic, validation, orchestration. No HTTP awareness.
- **Repositories** (`easyorario/repositories/`): Data access via Advanced Alchemy. No business logic.
- **Models** (`easyorario/models/`): SQLAlchemy ORM entities (User, Timetable, Revision, Constraint, Comment).
- **Guards** (`easyorario/guards/`): Role-based access control enforced declaratively on routes.

### Key Boundaries

- `services/llm.py` is the **sole** LLM API contact point. All prompt construction, calling, and response validation lives here.
- `services/solver.py` is the **sole** Z3 interface. Sync function, no HTTP or DB awareness — receives data, returns data.
- Controllers never check permissions directly — guards handle it.
- Use Litestar's dependency injection, never manual service instantiation.

### Async Pattern

Long-running operations (Z3 solving, LLM translation) use Litestar background tasks. Job status stored in DB, frontend polls `/solver/status/{job_id}` every 3 seconds via vanilla JS.

### Templates & Frontend

- `templates/base.html` → `templates/pages/` → `templates/partials/`
- Oat UI via CDN (unpkg @knadh/oat), custom CSS only for timetable grid
- No JS framework, no build step. Minimal vanilla JS for polling.

## Development Workflow

### Always update CLAUDE.md

After a change, check to see if the CLAUDE.md file must be updated.

### TDD (Mandatory)

Red-green-refactor cycle for every feature:
1. **Red**: Write one small failing test. Name: `test_{action}_{condition}_{expected_result}`
2. **Green**: Minimum code to pass
3. **Refactor**: Only if needed, all tests stay green
4. Never write production code without a failing test first.

### Version Control — jj (Jujutsu)

**Use jj, never raw git commands.** This is a colocated repo (jj + git share `.git`). Git is only the storage backend.

**Mental model: The working copy IS a commit.** There is no staging area, no "uncommitted changes." Every file edit is automatically snapshotted into the current working-copy commit (`@`) the next time any `jj` command runs. The question is never "what do I commit?" — everything is already in a commit. The question is "do I start a new change?" or "do I reorganize my changes?"

**Core commands:**
```bash
jj new                        # Start a new empty change on top of @
jj new -m "description"       # Start a new change with a message
jj describe -m "message"      # Set/update description of current change (no new commit)
jj commit -m "message"        # Shorthand for: jj describe + jj new
jj edit <change-id>           # Go back to edit any commit; descendants auto-rebase
jj diff                       # See what changed in working copy
jj log                        # Show commit graph (@ = working copy)
```

**Reorganizing changes:**
```bash
jj squash                     # Move working copy changes into parent
jj split                      # Split current commit interactively
jj absorb                     # Auto-distribute changes to correct ancestor commits
jj rebase -d main@origin      # Rebase onto latest main (conflicts don't block)
jj abandon <change-id>        # Remove a commit (children rebase onto its parent)
```

**Working with remotes (GitHub):**
```bash
jj git fetch                  # Fetch from remote (there is no jj git pull)
jj bookmark create <name>     # Create a named pointer (≈ git branch, but doesn't auto-advance)
jj bookmark set <name>        # Move bookmark to current commit
jj git push --bookmark <name> # Push bookmark as git branch
```

**Diff and status commands:**
- Use `jj diff --no-pager --git` to output diffs in git format (for piping, reviewing, etc.)
- Use `jj status` to see which files changed in a commit (not `jj diff`)
- Use `jj diff --stat` only when you need to see how much data was added/removed

**Key differences from git:**
- No `git add` — files are auto-tracked, always part of the working-copy commit
- No `git stash` — just `jj new @-` to park current work and start fresh from parent
- No need to commit before switching — `jj new` or `jj edit` anywhere, work is always safe
- Bookmarks don't auto-advance — you must `jj bookmark set` to move them
- Conflicts don't block rebases — they're recorded in commits, resolve at your leisure
- Change IDs are stable across rewrites (rebases, amends); commit IDs change like git SHAs
- `jj undo` undoes any operation; `jj op log` shows full operation history

**Revsets (query language for selecting commits):**
```bash
jj log -r "trunk()..@"        # Your work since main
jj log -r "conflicts()"       # Find conflicted commits
jj log -r "bookmarks()"       # All bookmarked commits
# @=working copy, @-=parent, @--=grandparent, ::x=ancestors, x::=descendants
```

## Naming Conventions

- **Python**: `snake_case` (functions, variables, modules), `PascalCase` (classes), `UPPER_SNAKE_CASE` (constants)
- **URLs**: `kebab-case`, Italian paths (`/orario/{id}/vincoli`, `/accedi`, `/registrati`)
- **JSON**: `snake_case` (no camelCase)
- **Database**: `snake_case` tables (plural), `{table_singular}_id` for FKs, `ix_{table}_{column}` for indexes
- **Tests**: `tests/` mirrors `easyorario/` structure. e.g., `easyorario/controllers/auth.py` → `tests/controllers/test_auth.py`

## Key Rules

- **Run `just check` before every commit** — ensures format, lint, and typecheck pass
- **Run `just test` separately** — tests are not included in `just check`
- **Never use `from __future__ import annotations`** — we target Python 3.14+, all modern type syntax is native
- User-facing text in **Italian**, logs and code in **English**
- Never hardcode Italian strings in Python — use templates or `i18n/errors.py` message mappings
- Use `structlog` for all logging, never `print()`
- Never log API keys or session secrets
- LLM API keys are **not persisted** — user provides per session
- All external LLM calls go through `services/llm.py`, all Z3 calls through `services/solver.py`
- **Create a jj bookmark** at the start of each story implementation

## Planning Documents

Architecture decisions, epics, stories, and UX design are in `_bmad-output/planning-artifacts/`. Implementation stories for the current sprint are in `_bmad-output/implementation-artifacts/`. Consult these before implementing features.
