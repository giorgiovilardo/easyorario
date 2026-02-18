# Sprint Change Proposal — Session Store & retrieve_user_handler

**Date:** 2026-02-18
**Triggered by:** Story 1.3 (User Login & Session Management) — test failures with MemoryStore/SQLAlchemy interaction
**Change scope:** Minor — documentation alignment only
**Status:** Approved

## 1. Issue Summary

During Story 1.3 implementation, the `retrieve_user_handler` originally queried the database on every request to load the User. With StaticPool in tests (in-memory SQLite), opening a separate DB session triggered ROLLBACK on the shared connection, corrupting state — especially around redirect flows where `AsyncTestClient` follows redirects by default, invoking `retrieve_user_handler` multiple times.

The fix was to cache `user_id`, `email`, and `role` in the HTTP session at login, then reconstruct a transient `User` in `retrieve_user_handler` without any DB query. This resolved all test failures and is architecturally sound.

The `MemoryStore` session backend (vs. the architecture-specified "DB-backed cookie sessions") is a separate concern — it causes no functional bugs and is acceptable for the PoC. Migration to a persistent store is a one-line change deferred to pre-deployment hardening.

## 2. Impact Analysis

### Epic Impact
- **Epic 1** (User Access & System Foundation): No scope change. Story 1.3's implementation is correct.
- **Epics 2-5**: No impact. Session storage backend is transparent to all downstream features.

### Artifact Conflicts
- **architecture.md**: Says "DB-backed cookie sessions" — needs update to reflect MemoryStore + session-cached user pattern
- **epics.md**: Story 1.3 AC says "DB-backed cookie"; Additional Requirements section repeats the architecture text
- **1-3-user-login-session-management.md**: Dev notes contain outdated code sample and completion notes referencing `db_config.get_session()`
- **No code changes needed** — `app.py` is already correct, including its TODO comment

### Technical Impact
None. The session-cached user pattern is the correct long-term approach regardless of session store backend.

## 3. Recommended Approach

**Direct Adjustment** — align documentation with the actual implementation.

- **Effort:** Low (7 text edits across 3 files)
- **Risk:** Low (no code changes, no behavior changes)
- **Timeline impact:** None

### Production Migration Path (for reference, not in sprint)

The session-cached `retrieve_user_handler` pattern is correct for production. The only deployment change is swapping the session store:

| Option | When to use | Change |
|--------|-------------|--------|
| `FileStore` | Single VPS, single worker | `stores={"sessions": FileStore(path=Path("./session_data"))}` |
| `RedisStore` | Multi-worker or shared state needed | `stores={"sessions": RedisStore.with_client(url="redis://...")}` |
| Custom DB store | Homogeneous stack preference | Implement Litestar `Store` protocol with a `sessions` table |

Key design decisions for production:
- **Never store SQLAlchemy ORM objects in the HTTP session** — they don't survive serialization round-trips. Store plain keys (user_id, email, role).
- **Session-cached user reconstruction is preferred** over DB queries per request — eliminates a round-trip and avoids StaticPool test issues.
- **If immediate role revocation is needed later**, add session invalidation on role change rather than querying the DB per request.

## 4. Detailed Change Proposals

### Proposal 1 — `architecture.md` (Authentication & Security)
**OLD:** `Authentication: Session-based with DB-backed cookie sessions (Litestar built-in session middleware)`
**NEW:** `Authentication: Session-based with server-side sessions (Litestar built-in session middleware, MemoryStore for PoC). User attributes cached in HTTP session at login — no DB query on subsequent requests. Persistent store (FileStore/Redis) deferred to pre-deployment hardening.`

### Proposal 2 — `epics.md` (Additional Requirements)
**OLD:** `Auth: Session-based with DB-backed cookie sessions (Litestar middleware), Argon2 via argon2-cffi, CSRF middleware on all form endpoints`
**NEW:** `Auth: Session-based with server-side sessions (Litestar middleware, MemoryStore for PoC), Argon2 via argon2-cffi, CSRF middleware on all form endpoints`

### Proposal 3 — `epics.md` (Story 1.3 AC #1)
**OLD:** `Then a session is created (DB-backed cookie) and I am redirected to /dashboard`
**NEW:** `Then a session is created (server-side, cookie-identified) and I am redirected to /dashboard`

### Proposal 4 — `1-3-user-login-session-management.md` (Task 1.1)
**OLD:** `loads User from DB using user_id stored in session dict`
**NEW:** `reconstructs User from session-cached attributes (user_id, email, role), no DB query`

### Proposal 5 — `1-3-user-login-session-management.md` (Dev Notes code sample + key points)
Updated `retrieve_user_handler` code sample to match actual implementation. Removed `alchemy_config.get_session()` reference.

### Proposal 6 — `1-3-user-login-session-management.md` (Architecture Deviation section)
Expanded to document both the MemoryStore deviation AND the session-cached user pattern as a deliberate architectural choice, including production migration guidance.

### Proposal 7 — `1-3-user-login-session-management.md` (Completion Notes)
Updated to reflect session-cached reconstruction instead of `db_config.get_session()`.

## 5. Implementation Handoff

**Scope:** Minor — direct implementation, no backlog reorganization needed.

**Deliverables:**
- [x] Sprint Change Proposal document (this file)
- [x] 7 text edits applied to 3 planning/implementation artifacts
- [x] No code changes required

**Success criteria:**
- All documentation accurately reflects the session-cached user pattern
- No references to `db_config.get_session()` or "DB-backed cookie sessions" remain in the context of the current implementation
- Production migration path is documented for future reference
