---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]
lastStep: 14
status: 'complete'
completedAt: '2026-02-16'
inputDocuments:
  - 'docs/PRD.md'
  - '_bmad-output/planning-artifacts/architecture.md'
workflowType: 'ux-design'
project_name: 'easyorario'
user_name: 'MasterArchitect'
date: '2026-02-16'
designConstraints:
  - 'Keep everything very simple'
  - 'Use oat.ink (Oat UI) as the CSS framework'
  - 'Desktop-only PoC'
  - 'Server-rendered Jinja2 templates'
  - 'Minimal JavaScript'
---

# UX Design Specification easyorario

**Author:** MasterArchitect
**Date:** 2026-02-16

---

<!-- UX design content will be appended sequentially through collaborative workflow steps -->

## Executive Summary

### Project Vision

Easyorario automates single-class timetable creation for Italian schools. Professors express scheduling rules in plain Italian; an LLM translates them to formal constraints; a solver generates a valid timetable. The UX goal is radical simplicity — a linear, step-by-step flow that feels like a conversation, not a form-filling exercise. Desktop-only PoC using Oat UI for a clean, lightweight interface.

### Target Users

- **Responsible Professor** (primary): Non-technical admin faculty. Creates timetables, inputs constraints in natural Italian, manages revisions, finalizes for publication. Needs zero technical knowledge to use the system.
- **Professor** (secondary): Teaching faculty. Reviews draft timetables, leaves comments on specific timeslots or overall schedule. Read-only plus comments.
- **Student** (tertiary, deferred): Views finalized timetable via public link. No authentication.

### Key Design Challenges

- **Constraint verification UX**: The NL-to-formal translation is the product's core. Users must clearly see what they wrote, what the system understood, and approve/reject each constraint individually. Trust in the translation is essential.
- **Async operation feedback**: LLM translation (up to 10s) and timetable solving (up to 5min) are long-running. Users need clear, simple progress indication via polling — no spinners that feel broken.
- **Dense timetable grid**: 6 days x 6-8 slots with subject, teacher, and room per cell. Must be scannable and not overwhelming on desktop.

### Design Opportunities

- **Simplicity as differentiator**: Competitors require technical expertise and rigid forms. A clean, linear flow with natural language input can feel dramatically easier.
- **Oat UI semantic approach**: Leverage native HTML styling for a consistent, lightweight UI with minimal custom CSS. The framework's simplicity matches the product's philosophy.
- **Step-by-step workflow**: The natural progression (create → constrain → verify → generate → review → finalize) maps to discrete pages, making the experience feel guided and manageable.

## Core User Experience

### Defining Experience

The core loop is: **write rules → verify understanding → generate timetable**. A Responsible Professor types scheduling constraints as natural Italian sentences in a simple textarea. The system translates each constraint into a structured interpretation (human-readable) and a formal Z3 representation (hidden by default, expandable for debugging). The user approves or rejects each interpretation. Once all constraints are verified, the user triggers timetable generation.

### Platform Strategy

- Desktop-only web application (mouse/keyboard)
- Server-rendered pages via Jinja2 + Oat UI
- No offline capability needed
- No special device features
- Minimal JavaScript — only vanilla JS polling for async solver status

### Effortless Interactions

- **Constraint input**: A plain textarea. Type Italian sentences, hit submit. No forms, no dropdowns, no syntax.
- **Constraint verification**: One card per constraint showing original text, structured interpretation, and collapsible Z3 debug output. Single approve/reject action per card.
- **Timetable viewing**: A clean HTML table. 6 columns (days) x time slots (rows). Subject, teacher, room per cell. Scannable at a glance.

### Critical Success Moments

1. **"It understood me"** — The user sees a correct interpretation of their Italian constraint. Trust is established.
2. **"It works"** — A valid timetable grid appears after generation. The payoff moment.
3. **"My colleague can see it"** — Sharing a link and getting comments back closes the collaboration loop.

### Experience Principles

1. **No technical knowledge required** — The user never writes syntax, never sees Z3 (unless they choose to expand debug info), never learns a tool. They write Italian and approve interpretations.
2. **Linear progression** — Each page is one step: create → input constraints → verify → generate → review → finalize. No branching, no complex navigation.
3. **Show, don't explain** — The verification card shows original vs. interpretation side by side. No instructions needed.
4. **Simple over clever** — Plain HTML elements (textarea, table, details, buttons). Oat UI semantic styling. No custom components beyond what Oat provides.

## Design System

### Framework

Oat UI (oat.ink) — 6KB CSS, 2.2KB JS. Semantic HTML-first. No custom design tokens, no overrides. Use Oat defaults for everything.

### Elements Used

- **Typography**: Native headings, paragraphs, links — Oat styles them directly
- **Buttons**: Native `<button>` elements. Primary action buttons for "Genera Orario", "Approva", etc.
- **Forms**: Native `<textarea>` for constraint input, `<input>` for login/registration fields
- **Tables**: Native `<table>` for timetable grid display
- **Cards**: For constraint verification cards (original text + interpretation + Z3 debug)
- **Dialog**: Native `<dialog>` for confirmation modals (delete timetable, finalize)
- **Accordion/Details**: `<details>` for collapsible Z3 debug output on constraint cards
- **Alert**: For flash messages (success, error, warning) in Italian
- **Spinner/Progress**: For async operation feedback (LLM translation, solver running)
- **Badge**: For constraint status (pending/verified/rejected) and timetable status (draft/final)
- **Tabs**: Oat web component for switching between revisions on timetable view
- **Toast**: For notification feedback (comment added, constraint saved)
- **Grid**: 12-column grid for page layout

### Custom CSS

One file: `app.css`. Only for:
- Timetable grid cell sizing and density
- Constraint card layout (if Oat cards need minor adjustments)
- Nothing else

## Page Map & User Journeys

### Site Map

```
/                           → Landing / redirect to dashboard
/accedi                     → Login
/registrati                 → Registration
/dashboard                  → List of user's timetables
/orario/nuovo               → Create new timetable (class info + parameters)
/orario/{id}/vincoli        → Constraint input (textarea) + list of existing constraints
/orario/{id}/vincoli/verifica → Constraint verification (card-by-card approve/reject)
/orario/{id}/genera         → Trigger generation + progress/polling page
/orario/{id}/revisione/{n}  → View timetable grid + comments for a specific revision
/orario/{id}/condividi      → Sharing settings + public link
/orario/{id}/pubblica       → Public final timetable view (no auth)
/impostazioni               → LLM endpoint configuration
```

### Journey: Responsible Professor Creates Timetable

1. **Login** (`/accedi`) → Standard email/password form
2. **Dashboard** (`/dashboard`) → Sees list of timetables, clicks "Nuovo Orario"
3. **Create** (`/orario/nuovo`) → Enters class name, school year, weekly hours, subject list, teacher assignments → Saves, redirected to constraints page
4. **Constraints** (`/orario/{id}/vincoli`) → Textarea at top, types constraints in Italian, submits one at a time. List of submitted constraints below with status badges (pending/verified/rejected)
5. **Verify** (`/orario/{id}/vincoli/verifica`) → Card-by-card flow. Each card shows: original text, structured interpretation, collapsible Z3 debug. Approve or reject each. Rejected ones return to constraint list for editing.
6. **Generate** (`/orario/{id}/genera`) → Button to start. Shows spinner/progress. Polls every 3s. On success: redirected to revision view. On failure: shows conflict explanation in Italian, link back to constraints.
7. **Review** (`/orario/{id}/revisione/1`) → Timetable grid (table). Tabs for switching revisions if multiple exist. Comment section below.
8. **Finalize** → Button on revision view to mark as final. Confirmation dialog. Generates public link.

### Journey: Professor Reviews

1. Opens shared link → `/orario/{id}/revisione/{n}` (requires auth for drafts)
2. Views timetable grid
3. Clicks on a timeslot or uses comment form below → submits comment
4. Done

### Journey: Public View

1. Opens public link → `/orario/{id}/pubblica`
2. Sees finalized timetable grid. No auth. No comments. Read-only.

## Key Interaction Patterns

### Constraint Input

- Single `<textarea>` with a "Aggiungi vincolo" (Add constraint) button
- One constraint per submission (keeps translations atomic)
- After submit: constraint appears in list below with "pending" badge
- User can add multiple constraints before moving to verification

### Constraint Verification

- Accessed via "Verifica vincoli" button when pending constraints exist
- Sequential card flow — one constraint at a time, or all visible as a scrollable list
- Each card:
  - **Original text** (what the user typed)
  - **Interpretation** (structured: entity → restriction → scope, in Italian)
  - **Z3 debug** (collapsible `<details>`, shows formal representation)
  - **Actions**: "Approva" (primary button) / "Rifiuta" (secondary button)
- Approved → badge turns green, constraint locked
- Rejected → badge turns red, user can edit and resubmit

### Timetable Generation

- "Genera orario" button (disabled until ≥1 verified constraint exists)
- On click: POST to solver endpoint, page shows Oat `<progress>` element + "Generazione in corso..." text
- Vanilla JS polls `/solver/status/{job_id}` every 3 seconds
- On success: redirect to revision view
- On failure: Oat `<alert>` with Italian error message + "Modifica vincoli" link
- Timeout after 5 minutes: show timeout message

### Timetable Grid

- HTML `<table>` — 7 columns (header + Mon-Sat), rows = time slots
- Each cell: subject name (bold), teacher name, room — stacked in the cell
- Empty cells for free periods
- Compact but readable at desktop widths

### Comments

- Below the timetable grid on revision view
- Simple form: optional timeslot reference (dropdown of slots) + textarea + submit
- Comments listed chronologically with author, timestamp, referenced slot
