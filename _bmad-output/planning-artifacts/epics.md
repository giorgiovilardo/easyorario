---
stepsCompleted: ['step-01-validate-prerequisites', 'step-02-design-epics', 'step-03-create-stories', 'step-04-final-validation']
inputDocuments:
  - 'docs/PRD.md'
  - '_bmad-output/planning-artifacts/architecture.md'
  - '_bmad-output/planning-artifacts/ux-design-specification.md'
---

# easyorario - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for easyorario, decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

FR-1: Natural Language Constraint Input (MUST) — System accepts constraint input in Italian natural language via multi-line text field. Supports constraint types: teacher availability, subject scheduling preferences, resource allocation, consecutive hour limits.

FR-2: Constraint Translation and Verification (MUST) — System translates natural language constraints to formal representation using configured LLM endpoint. Displays translated constraints in human-readable format for user verification. User can approve, edit, or reject translated constraints before solving.

FR-3: Constraint Conflict Detection (SHOULD) — System detects obvious constraint conflicts before solving (e.g., teacher double-booked, hour totals exceed capacity).

FR-4: Constraint Library Management (COULD) — User can save constraint sets as reusable templates and apply them to new timetables. [DEFERRED — post-MVP]

FR-5: Single-Class Timetable Generation (MUST) — System generates timetable satisfying all user-defined constraints for a single class section. Supports 6-day structure (Monday-Saturday) and 27-32 weekly hour slots.

FR-6: Timetable Regeneration (MUST) — User can modify constraints and regenerate timetable, creating new revision while preserving previous ones.

FR-7: Unsolvable Constraint Handling (MUST) — System detects when constraint set has no valid solution and provides conflict explanation in Italian.

FR-8: Week-Grid Timetable View (MUST) — Displays timetable in week-grid format (rows = time slots, columns = days) with subject, teacher, and classroom per cell.

FR-9: Timetable Sharing via Link (MUST) — Generates unique shareable URL for each revision; draft links require authentication; final links are public.

FR-10: Comment System (MUST) — Professors can add comments referencing specific timeslots or the overall timetable. [Note: real-time notification deferred per Architecture]

FR-11: User Authentication (MUST) — Email/password authentication for Responsible Professor and Professor roles.

FR-12: Role-Based Access Control (MUST) — Enforces permissions: Responsible Professor (full access), Professor (read + comment), Public (final view only).

FR-13: LLM Endpoint Configuration (MUST) — Responsible Professor configures LLM API endpoint (URL, API key, model identifier) via settings page. [Note: Architecture decision — keys stored per session only, not persisted]

FR-14: Timetable Finalization (MUST) — Responsible Professor marks revision as "Final"; timetable becomes publicly accessible and immutable.

FR-15: Timetable Deletion (SHOULD) — Draft timetables can be deleted; finalized timetables are archived instead.

FR-16: Revision History (SHOULD) — System maintains history of all revisions with timestamps; user can view previous revisions and their constraints.

### NonFunctional Requirements

NFR-1: Timetable Generation Latency (MUST) — P95 generation time ≤5 minutes for ≤20 constraints; P95 regeneration time ≤10 minutes.

NFR-2: Page Load Time (MUST) — P95 page load time ≤3 seconds on 4G mobile connection.

NFR-3: LLM Translation Latency (MUST) — P95 constraint translation time ≤10 seconds per constraint.

NFR-4: Concurrent User Capacity (SHOULD) — Supports ≥10 concurrent users and ≥3 simultaneous generation operations.

NFR-5: Authentication Security (MUST) — Passwords hashed using Argon2 (per Architecture); HTTPS enforced in production.

NFR-6: Authorization Enforcement (MUST) — User permissions validated on every API request; draft timetables inaccessible to unauthenticated users.

NFR-7: API Key Protection (MUST) — LLM API keys never logged or exposed in error messages. [Architecture: keys not persisted at all — exceeds requirement]

NFR-8: Data Privacy (MUST) — Minimal PII collection; no student identifiers required; data export (JSON) and account deletion supported.

NFR-9: Mobile Responsiveness (MUST) — [DEFERRED: Desktop-only PoC per Architecture conscious deviation]

NFR-10: Italian Language Interface (MUST) — All user-facing text in Italian; dates DD/MM/YYYY; times 24-hour clock.

NFR-11: Constraint Input Usability (MUST) — Constraint input requires no technical or programming knowledge; verification display uses plain Italian.

NFR-12: System Availability (SHOULD) — ≥95% uptime during peak usage (August-September).

NFR-13: Data Persistence (MUST) — Timetable data and constraints persist across server restarts; zero data loss under normal shutdown.

NFR-14: Error Handling (MUST) — User-friendly error messages in Italian for common failures; detailed server-side logging via structlog.

NFR-15: Code Documentation (SHOULD) — Critical functions include inline comments; system architecture documented.

NFR-16: Dependency Management (SHOULD) — All external dependencies declared with version pinning in pyproject.toml.

### Additional Requirements

**From Architecture:**

- Starter/scaffolding: No external starter template. Project scaffolding (directory structure, justfile, Dockerfile, Litestar app initialization, Alembic setup) is the first implementation story
- Database: SQLite with WAL mode via aiosqlite + Advanced Alchemy repository pattern; Alembic for migrations
- Auth: Session-based with server-side sessions (Litestar middleware, MemoryStore for PoC), Argon2 via argon2-cffi, CSRF middleware on all form endpoints
- LLM API keys: Not persisted — provided per session, stored in session data only
- Async operations: Litestar background tasks for Z3 solver (sync function auto-wrapped to thread pool); job status stored in DB; vanilla JS polling every 3 seconds
- Error handling: Custom exception hierarchy (EasyorarioError base), domain-specific exceptions (UnsolvableConstraintsError, LLMTranslationError, ConstraintConflictError), Italian error templates, structlog for server-side logging
- Process: TDD red-green-refactor cycle mandatory; jj (Jujutsu) for VCS, never raw git
- Controller → Service → Repository layered architecture with one-way dependencies
- LLM boundary: services/llm.py is sole point of contact with external LLM APIs
- Solver boundary: services/solver.py is sole Z3 interface, sync function, no HTTP/DB awareness
- Comment notifications: Deferred — no real-time push, Responsible Professor sees comments on next visit

**From UX Design:**

- Italian-language URL paths: /accedi, /registrati, /dashboard, /orario/{id}/vincoli, /orario/{id}/vincoli/verifica, /orario/{id}/genera, /orario/{id}/revisione/{n}, /orario/{id}/condividi, /orario/{id}/pubblica, /impostazioni
- One constraint per submission (atomic LLM translations)
- Card-by-card constraint verification flow with approve/reject per card
- Collapsible Z3 debug output on verification cards via <details> element
- Oat UI components: progress element for async ops, alert for errors, badge for status indicators, dialog for confirmations, tabs (web component) for revision switching, toast for notifications
- Timetable grid: HTML <table>, 7 columns (header + Mon-Sat), cells with subject/teacher/room stacked
- Comments section below timetable grid with optional timeslot reference dropdown
- Desktop-only PoC (no mobile responsive layout)

### FR Coverage Map

FR-1: Epic 2 — Natural Language Constraint Input
FR-2: Epic 3 — Constraint Translation & Verification
FR-3: Epic 3 — Constraint Conflict Detection
FR-4: Deferred — Constraint Library Management (post-MVP)
FR-5: Epic 4 — Single-Class Timetable Generation
FR-6: Epic 4 — Timetable Regeneration
FR-7: Epic 4 — Unsolvable Constraint Handling
FR-8: Epic 4 — Week-Grid Timetable View
FR-9: Epic 5 — Timetable Sharing via Link
FR-10: Epic 5 — Comment System
FR-11: Epic 1 — User Authentication
FR-12: Epic 1 — Role-Based Access Control
FR-13: Epic 3 — LLM Endpoint Configuration
FR-14: Epic 5 — Timetable Finalization
FR-15: Epic 5 — Timetable Deletion
FR-16: Epic 4 — Revision History

## Epic List

### Epic 1: User Access & System Foundation
Users can register, log in, and see a personalized dashboard listing their timetables. Includes project scaffolding, database setup, session-based authentication with Argon2, and role-based access control.
**FRs covered:** FR-11, FR-12

### Epic 2: Timetable Creation & Constraint Input
Responsible Professors can create timetables with class parameters (class name, school year, weekly hours, subjects, teachers) and input scheduling constraints in Italian natural language. Constraints are stored with "pending" status for later translation.
**FRs covered:** FR-1

### Epic 3: LLM Constraint Translation & Verification
The system translates natural language constraints into formal representations via a user-configured LLM endpoint. Users review, approve, or reject each translation with full transparency including collapsible Z3 debug output. Pre-solve conflict detection warns of obvious issues.
**FRs covered:** FR-2, FR-3, FR-13

### Epic 4: Timetable Generation & Review
The system generates valid timetables from verified constraints using the Z3 solver as a background task. Displays results in a week-grid view. Supports revision management with regeneration after constraint changes. Handles unsolvable constraints with Italian conflict explanations.
**FRs covered:** FR-5, FR-6, FR-7, FR-8, FR-16

### Epic 5: Collaboration, Sharing & Finalization
Professors can review draft timetables and leave comments referencing specific timeslots. Responsible Professors can finalize timetables for public access, share via unique URLs, and manage timetable lifecycle (deletion/archival).
**FRs covered:** FR-9, FR-10, FR-14, FR-15

## Epic 1: User Access & System Foundation

Users can register, log in, and see a personalized dashboard listing their timetables. Includes project scaffolding, database setup, session-based authentication with Argon2, and role-based access control.

### Story 1.1: Project Skeleton & Development Infrastructure

As a developer,
I want a minimal working Litestar application with development tooling,
So that I have a foundation to build features on.

**Acceptance Criteria:**

**Given** the project repository is cloned
**When** I run the dev server via justfile
**Then** a Litestar app starts and serves a minimal home page at `/`
**And** a health check endpoint at `/health` returns 200 with a DB connectivity check (`SELECT 1`)

**Given** the project needs database migrations
**When** I check the Alembic configuration
**Then** Alembic is configured with async SQLite (WAL mode) and can run migrations
**And** alembic.ini and alembic/env.py are present

**Given** the project needs containerization
**When** I build and run the Docker image
**Then** the app starts and serves requests

**Given** the project needs a task runner
**When** I check the justfile
**Then** commands exist for: dev server, tests, linting, Docker build

**Given** a new developer joins the project
**When** they read CLAUDE.md
**Then** they find modular documentation covering project structure, stack decisions, conventions, and development workflow

### Story 1.2: User Registration

As a Responsible Professor,
I want to register with my email and password,
So that I can create an account to manage timetables.

**Acceptance Criteria:**

**Given** I am on the registration page at `/registrati`
**When** I submit a valid email and password (≥8 characters)
**Then** a User is created with Argon2-hashed password and a role
**And** I am redirected to the login page with a success message in Italian

**Given** I submit a registration with an already-used email
**When** the form is processed
**Then** I see an Italian error message indicating the email is taken

**Given** I submit a password shorter than 8 characters
**When** the form is processed
**Then** I see an Italian validation error

**Given** the User model needs to be persisted
**When** I check the database
**Then** a `users` table exists with columns: id, email, hashed_password, role, created_at
**And** an Alembic migration was created for this table

### Story 1.3: User Login & Session Management

As a registered user,
I want to log in with my email and password,
So that I can access the system securely.

**Acceptance Criteria:**

**Given** I am on the login page at `/accedi`
**When** I submit valid credentials
**Then** a session is created (server-side, cookie-identified) and I am redirected to `/dashboard`

**Given** I submit invalid credentials
**When** the form is processed
**Then** I see an Italian error message and remain on the login page

**Given** I am logged in
**When** I click logout
**Then** my session is destroyed and I am redirected to `/accedi`

**Given** CSRF protection is enabled
**When** a form POST is submitted without a valid CSRF token
**Then** the request is rejected

**Given** I am not authenticated
**When** I try to access a protected page
**Then** I am redirected to `/accedi`

### Story 1.4: Dashboard & Role-Based Access Control

As a logged-in user,
I want to see a personalized dashboard,
So that I can view my timetables and access features appropriate to my role.

**Acceptance Criteria:**

**Given** I am logged in as a Responsible Professor
**When** I visit `/dashboard`
**Then** I see my timetables list (empty state with "Nuovo Orario" button for now)

**Given** I am logged in as a Professor
**When** I visit `/dashboard`
**Then** I see timetables I have previously accessed via shared links (empty state for now — access tracking implemented in Epic 5)
**And** I do not see the "Nuovo Orario" button

**Given** I am a Professor
**When** I attempt to access a Responsible Professor-only action
**Then** I receive a 403 Forbidden response

**Given** I am unauthenticated
**When** I attempt to access `/dashboard` or any draft timetable URL
**Then** I receive a 401 and am redirected to `/accedi`

**Given** I am authenticated and visit `/`
**When** the page loads
**Then** I am redirected to `/dashboard`

## Epic 2: Timetable Creation & Constraint Input

Responsible Professors can create timetables with class parameters and input scheduling constraints in Italian natural language. Constraints are stored with "pending" status for later translation.

### Story 2.1: Create New Timetable

As a Responsible Professor,
I want to create a new timetable by entering class information,
So that I have a timetable workspace to define scheduling constraints.

**Acceptance Criteria:**

**Given** I am logged in as a Responsible Professor on `/dashboard`
**When** I click "Nuovo Orario"
**Then** I am taken to `/orario/nuovo`

**Given** I am on the create timetable page
**When** I submit class identifier (e.g., "3A Liceo Scientifico"), school year, number of weekly hours, subject list, and teacher assignments
**Then** a Timetable is created with status "draft" and I am redirected to `/orario/{id}/vincoli`

**Given** the Timetable model needs to be persisted
**When** I check the database
**Then** a `timetables` table exists with columns: id, class_identifier, school_year, weekly_hours, subjects (JSON), teachers (JSON), status, owner_id, created_at
**And** an Alembic migration was created for this table

**Given** I am a Professor (not Responsible Professor)
**When** I try to access `/orario/nuovo`
**Then** I receive a 403 Forbidden response

### Story 2.2: Constraint Input in Natural Language

As a Responsible Professor,
I want to input scheduling constraints in Italian natural language,
So that I can define the rules for timetable generation without technical syntax.

**Acceptance Criteria:**

**Given** I am on `/orario/{id}/vincoli` for my timetable
**When** I type an Italian constraint in the textarea (e.g., "Prof. Rossi non può insegnare il lunedì mattina") and click "Aggiungi vincolo"
**Then** the constraint is saved with status "pending" and appears in the list below with a "pending" badge

**Given** I have submitted multiple constraints
**When** I view the constraints list
**Then** I see all constraints with their status badges (pending/verified/rejected) and original text

**Given** the Constraint model needs to be persisted
**When** I check the database
**Then** a `constraints` table exists with columns: id, timetable_id, natural_language_text, formal_representation (JSON, nullable), status, created_at
**And** an Alembic migration was created for this table

**Given** the textarea accepts Italian text
**When** I submit a constraint
**Then** the text field supports ≥500 characters and I can submit ≥10 constraints per timetable

**Given** pending constraints exist
**When** I view the page
**Then** I see a "Verifica vincoli" button linking to the verification flow (non-functional until Epic 3)

## Epic 3: LLM Constraint Translation & Verification

The system translates natural language constraints into formal representations via a user-configured LLM endpoint. Users review, approve, or reject each translation with full transparency including collapsible Z3 debug output. Pre-solve conflict detection warns of obvious issues.

### Story 3.1: LLM Endpoint Configuration

As a Responsible Professor,
I want to configure my LLM API endpoint,
So that the system can translate my constraints using my preferred AI provider.

**Acceptance Criteria:**

**Given** I am logged in as a Responsible Professor
**When** I visit `/impostazioni`
**Then** I see a form for LLM API base URL, API key, and model identifier

**Given** I submit valid LLM configuration
**When** the system validates connectivity with a test request
**Then** the configuration is stored in my session (not persisted to DB) and I see an Italian success message

**Given** I submit invalid LLM configuration (unreachable URL, bad API key)
**When** the system attempts the test request
**Then** I see an Italian error message explaining the failure

**Given** I have not configured an LLM endpoint
**When** I try to trigger constraint translation
**Then** I am redirected to `/impostazioni` with an Italian message to configure the endpoint first

### Story 3.2: Constraint Translation via LLM

As a Responsible Professor,
I want the system to translate my Italian constraints into formal representations,
So that they can be used by the constraint solver.

**Acceptance Criteria:**

**Given** I have pending constraints and a configured LLM endpoint
**When** I click "Verifica vincoli" on `/orario/{id}/vincoli`
**Then** each pending constraint is sent to the LLM for translation and I am taken to `/orario/{id}/vincoli/verifica`

**Given** the LLM processes a constraint
**When** translation completes
**Then** the constraint's formal_representation (JSON) is stored and its status changes to "pending" verification

**Given** the LLM is unavailable or returns an error
**When** translation fails for a constraint
**Then** I see an Italian error message and can retry or rephrase the constraint

**Given** the LLM returns a malformed constraint representation
**When** schema validation rejects it
**Then** I see an Italian message asking me to rephrase the constraint

**Given** performance requirements (NFR-3)
**When** a constraint is translated
**Then** the translation completes within 10 seconds (P95)

### Story 3.3: Constraint Verification & Approval

As a Responsible Professor,
I want to review each translated constraint and approve or reject it,
So that I can trust the system's interpretation before generating a timetable.

**Acceptance Criteria:**

**Given** I am on `/orario/{id}/vincoli/verifica` with translated constraints
**When** I view the page
**Then** I see a card for each constraint showing: original Italian text, structured human-readable interpretation, and a collapsible `<details>` section with the Z3 formal representation

**Given** I am reviewing a constraint card
**When** I click "Approva"
**Then** the constraint status changes to "verified" and its badge turns green

**Given** I am reviewing a constraint card
**When** I click "Rifiuta"
**Then** the constraint status changes to "rejected" with a red badge and I can edit the original text and resubmit for re-translation

**Given** all constraints have been reviewed
**When** at least one is verified
**Then** I see a "Genera orario" link/button (pointing to the generation flow in Epic 4, non-functional until then)

### Story 3.4: Pre-Solve Constraint Conflict Detection

As a Responsible Professor,
I want the system to detect obvious constraint conflicts before generation,
So that I can fix issues without waiting for the solver to fail.

**Acceptance Criteria:**

**Given** I have multiple verified constraints
**When** the system checks for conflicts
**Then** it identifies teacher double-bookings and hour-total mismatches with 100% accuracy

**Given** a conflict is detected
**When** I view the constraints page
**Then** I see an Italian warning identifying the conflicting constraints by description

**Given** no conflicts are detected
**When** I view the constraints page
**Then** no warning is shown and generation can proceed normally

## Epic 4: Timetable Generation & Review

The system generates valid timetables from verified constraints using the Z3 solver as a background task. Displays results in a week-grid view. Supports revision management with regeneration after constraint changes. Handles unsolvable constraints with Italian conflict explanations.

### Story 4.1: Timetable Generation with Z3 Solver

As a Responsible Professor,
I want to generate a timetable from my verified constraints,
So that I get a valid schedule without manual conflict resolution.

**Acceptance Criteria:**

**Given** I have ≥1 verified constraint and am on `/orario/{id}/genera`
**When** I click "Genera orario"
**Then** a background task is spawned for the Z3 solver and I see a progress indicator with "Generazione in corso..." text

**Given** a generation job is running
**When** I am on the generation page
**Then** vanilla JS polls `/solver/status/{job_id}` every 3 seconds for status updates

**Given** the solver completes successfully
**When** the poll returns "completed"
**Then** a Revision is created with the generated grid data (JSON) and constraints snapshot, and I am redirected to `/orario/{id}/revisione/1`

**Given** the Revision model needs to be persisted
**When** I check the database
**Then** a `revisions` table exists with columns: id, timetable_id, revision_number, grid_data (JSON), constraints_snapshot (JSON), created_at
**And** an Alembic migration was created for this table

**Given** performance requirements (NFR-1)
**When** the solver runs with ≤20 constraints
**Then** generation completes within 5 minutes (P95)

### Story 4.2: Unsolvable Constraint Handling

As a Responsible Professor,
I want clear feedback when my constraints cannot be satisfied,
So that I know which constraints to modify.

**Acceptance Criteria:**

**Given** a generation job is running
**When** the solver determines the constraints are unsolvable
**Then** the job status changes to "failed" with a conflict explanation

**Given** the poll returns "failed"
**When** I view the generation page
**Then** I see an Italian error message identifying ≥1 conflicting constraint pair and a "Modifica vincoli" link back to `/orario/{id}/vincoli`

**Given** the solver exceeds 5 minutes
**When** the timeout is reached
**Then** the job is terminated and I see an Italian timeout message with a link to modify constraints

**Given** generation failed
**When** I return to constraints
**Then** all my previous constraint data is intact (no data loss)

### Story 4.3: Week-Grid Timetable View

As a Responsible Professor,
I want to see my generated timetable in a week-grid format,
So that I can review the schedule at a glance.

**Acceptance Criteria:**

**Given** a revision exists for my timetable
**When** I visit `/orario/{id}/revisione/{n}`
**Then** I see an HTML `<table>` with 7 columns (header + Monday-Saturday) and rows for each time slot

**Given** the timetable grid is displayed
**When** I look at a cell
**Then** I see the subject name (bold), teacher name, and room stacked within the cell
**And** empty cells are shown for free periods

**Given** the page renders
**When** I view it on a desktop browser
**Then** the table is compact but readable without horizontal scrolling

### Story 4.4: Timetable Regeneration & Revision History

As a Responsible Professor,
I want to modify constraints and regenerate, keeping previous revisions,
So that I can iterate on the timetable and compare versions.

**Acceptance Criteria:**

**Given** I have a generated timetable with revision 1
**When** I go back to constraints, modify them, and regenerate
**Then** a new revision (revision 2) is created while revision 1 remains accessible

**Given** multiple revisions exist
**When** I visit `/orario/{id}/revisione/{n}`
**Then** I can switch between revisions using Oat UI tabs

**Given** I view a previous revision
**When** I look at the revision
**Then** I see the timetable grid and the constraints snapshot that produced it

**Given** performance requirements (NFR-1)
**When** I regenerate
**Then** regeneration completes within 10 minutes (P95)

**Given** revision history requirements (FR-16)
**When** the system stores revisions
**Then** it maintains ≥10 revisions per timetable with timestamps

## Epic 5: Collaboration, Sharing & Finalization

Professors can review draft timetables and leave comments referencing specific timeslots. Responsible Professors can finalize timetables for public access, share via unique URLs, and manage timetable lifecycle (deletion/archival).

### Story 5.1: Comment System

As a Professor,
I want to add comments on a timetable revision,
So that I can provide feedback on scheduling issues.

**Acceptance Criteria:**

**Given** I am logged in and viewing `/orario/{id}/revisione/{n}`
**When** I see the comment section below the timetable grid
**Then** I see a form with an optional timeslot reference dropdown and a textarea

**Given** I submit a comment with text (and optionally a timeslot reference)
**When** the form is processed
**Then** the comment is saved and appears in the chronological list with my name, timestamp, and referenced timeslot

**Given** the Comment model needs to be persisted
**When** I check the database
**Then** a `comments` table exists with columns: id, revision_id, author_id, timeslot_reference (nullable), text, created_at
**And** an Alembic migration was created for this table

**Given** comments exist on a revision
**When** any user views the revision
**Then** all comments are displayed chronologically with author, timestamp, and referenced slot

### Story 5.2: Timetable Sharing via Link

As a Responsible Professor,
I want to share my timetable via a unique link,
So that colleagues can review and comment on drafts.

**Acceptance Criteria:**

**Given** I am the owner of a timetable
**When** I visit `/orario/{id}/condividi`
**Then** I see a unique shareable URL for the current revision and a copy button

**Given** a Professor opens a shared draft link
**When** they are authenticated
**Then** they can view the timetable grid and comment section
**And** the system records their access so the timetable appears on their dashboard

**Given** a Professor opens a shared draft link
**When** they are not authenticated
**Then** they are redirected to `/accedi` and returned to the timetable after login

**Given** a timetable access record is created
**When** the Professor visits `/dashboard`
**Then** the timetable appears in their "accessed timetables" list

### Story 5.3: Timetable Finalization & Public View

As a Responsible Professor,
I want to mark a timetable as final,
So that students and staff can access it via a public link without authentication.

**Acceptance Criteria:**

**Given** I am viewing a revision of my timetable
**When** I click "Finalizza" and confirm via the `<dialog>` confirmation modal
**Then** the timetable status changes to "final" and a public link is generated

**Given** the timetable is finalized
**When** anyone visits `/orario/{id}/pubblica`
**Then** they see the finalized timetable grid without authentication required
**And** no comments, constraints, or draft data is visible

**Given** a timetable is finalized
**When** I try to modify constraints or regenerate
**Then** the actions are blocked and I see an Italian message that the timetable is finalized

**Given** the public link is active
**When** the page loads
**Then** it renders within 3 seconds (NFR-2)

### Story 5.4: Timetable Deletion & Archival

As a Responsible Professor,
I want to delete draft timetables or archive finalized ones,
So that I can manage my timetable workspace.

**Acceptance Criteria:**

**Given** I own a draft timetable
**When** I click delete and confirm via the `<dialog>` confirmation modal
**Then** the timetable and all associated data (constraints, revisions, comments) are deleted

**Given** I own a finalized timetable
**When** I click delete
**Then** the timetable is archived (hidden from dashboard, public link deactivated) rather than permanently deleted

**Given** a timetable is deleted or archived
**When** I visit `/dashboard`
**Then** the timetable no longer appears in my active list
