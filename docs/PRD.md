---
workflowType: 'prd'
workflow: 'edit'
classification:
  domain: 'education'
  projectType: 'web-application'
  complexity: 'small'
stepsCompleted: ['step-e-01-discovery', 'step-e-01b-legacy-conversion', 'step-e-02-review', 'step-e-03-edit']
lastEdited: '2026-02-16'
editHistory:
  - date: '2026-02-16'
    changes: 'Full BMAD restructuring from legacy format'
---

# Easyorario

## Executive Summary

### Problem Statement

Italian school professors face a time-consuming manual process when creating class timetables at the start of each school year. They must balance numerous constraints (teacher availability, subject requirements, classroom capacity, student needs) without automated tools that understand the domain-specific rules of Italian education.

### Solution

Easyorario automates single-class timetable generation using constraint solving technology. Professors input scheduling rules in natural language (Italian), which are translated into formal constraints and solved algorithmically to produce valid timetables.

### Differentiator

Existing timetabling systems require technical expertise or rigid form-based input. Easyorario uses an LLM-powered constraint translation layer that allows non-technical users to express complex scheduling rules conversationally. The system translates natural language to formal constraints, solves them, and produces timetables without requiring professors to learn constraint syntax.

### Target Users

- **Responsible Professors**: Administrative faculty who create and manage timetables (primary users)
- **Professors**: Teaching faculty who review and provide feedback on timetable drafts (secondary users)
- **Students**: End consumers who view finalized timetables (tertiary users)

### Vision

Enable Italian schools to generate conflict-free, constraint-compliant timetables in hours instead of days, reducing administrative burden and allowing faster iteration based on stakeholder feedback.

## Success Criteria

**SC-1: Time Savings**
- Reduce timetable creation time from baseline of 8-16 hours (manual process) to <2 hours for initial draft generation
- Measurement: Time from constraint input completion to first valid timetable

**SC-2: Constraint Translation Accuracy**
- Achieve ≥85% accuracy in natural language constraint translation (percentage of user-stated constraints correctly converted to formal constraints)
- Measurement: Audit sample of 20 constraint translations per timetable against expected formal representation

**SC-3: Solution Quality**
- Generate valid timetables (satisfying all MUST constraints) in ≥90% of cases on first solve attempt
- Measurement: Percentage of solve attempts producing constraint-satisfying output

**SC-4: User Adoption**
- Achieve ≥3 complete timetables created by different Responsible Professors within first academic year
- Measurement: Count of timetables marked "final" in production system

**SC-5: Iteration Efficiency**
- Support ≥3 revision cycles per timetable with <10 minute regeneration time per revision
- Measurement: System response time from constraint modification to new timetable output

## Product Scope

### MVP (First Iteration)

**In Scope:**
- Single-class timetable generation (one class section, e.g., "3A Liceo Scientifico")
- Web-based user interface accessible via browser
- User-configurable LLM endpoint (OpenAI-compatible API format)
- Timetable revision workflow with comment capability
- Natural language constraint input in Italian
- Responsible Professor and Professor roles only

**Rationale:** Validates core differentiator (LLM constraint translation) and workflow (create → review → finalize) with minimal complexity. Single-class scope reduces solver complexity and data modeling requirements.

**Out of Scope (MVP):**
- Multi-class timetable coordination (multiple sections with shared teachers/resources)
- Student login and authentication
- Mobile native applications
- Constraint templates or libraries
- Integration with school management systems (SIS)
- Multi-language support (English, German, etc.)

**Rationale:** Multi-class coordination exponentially increases constraint complexity and solver runtime; deferred to validate single-class approach first. Student login provides minimal value over public view links and introduces GDPR compliance overhead; deferred pending user research on necessity.

### Growth Phase (Post-MVP)

- Multi-class timetable generation with resource sharing
- Student role with authenticated access
- Constraint template library for common scenarios
- Export to PDF and iCalendar formats
- Integration with common Italian SIS platforms (Axios, Nuvola, Spaggiari)

### Vision Phase

- District-level timetabling across multiple schools
- Machine learning-based constraint suggestion from historical timetables
- Mobile applications (iOS/Android)
- Advanced analytics (teacher workload distribution, classroom utilization)

### Personas

**Persona 1: Responsible Professor**
- **Role:** Administrative faculty member (e.g., vice principal, department head)
- **Responsibilities:** Create timetables, define scheduling constraints, manage revision cycles, finalize timetables for publication
- **Technical proficiency:** Basic computer literacy; no programming or technical constraint syntax knowledge
- **Goals:** Generate valid timetables quickly, minimize manual conflict resolution, incorporate feedback from teaching staff
- **System permissions:** Full access (create, edit, delete timetables; manage constraints; publish final versions)

**Persona 2: Professor**
- **Role:** Teaching faculty member
- **Responsibilities:** Review timetable drafts, identify conflicts with personal availability or pedagogical concerns, provide feedback via comments
- **Technical proficiency:** Basic computer literacy
- **Goals:** Ensure assigned teaching hours align with availability, identify scheduling issues early
- **System permissions:** Read-only access to draft and final timetables; comment creation on revisions

**Persona 3: Student**
- **Role:** Enrolled student in class section
- **Responsibilities:** View finalized timetable to know when/where to attend classes
- **Technical proficiency:** Basic computer literacy (smartphone/tablet users)
- **Goals:** Access current timetable, identify class schedule changes
- **System permissions:** Read-only access to finalized timetables only; no access to constraints or draft versions; no authentication required (public view link)

## User Journeys

### Journey 1: Responsible Professor Creates Timetable

**Actors:** Responsible Professor

**Preconditions:** User has authenticated; LLM endpoint configured in system settings

**Steps:**
1. User navigates to "Create New Timetable" page
2. User enters class identifier (e.g., "3A Liceo Scientifico, A.S. 2026-2027")
3. User enters timetable parameters (number of weekly hours, subject distribution, teacher assignments)
4. User inputs scheduling constraints in natural language Italian (e.g., "Prof. Rossi non può insegnare il lunedì mattina", "Matematica deve essere nelle prime due ore del giorno")
5. System displays interpreted constraints for user verification
6. User confirms or edits interpreted constraints
7. User initiates timetable generation
8. System processes constraints and returns generated timetable (or error if unsolvable)
9. User reviews generated timetable, saves as "Draft Revision 1"
10. User shares timetable link with Professor colleagues for review

**Success Criteria:**
- User completes constraint input without requiring technical assistance
- System generates valid timetable satisfying all constraints
- Total time from step 1 to step 9 <2 hours

**Alternative Flows:**
- 8a. If constraints unsolvable, system returns conflict explanation; user returns to step 4 to modify constraints

### Journey 2: Professor Reviews Draft Timetable

**Actors:** Professor (reviewer), Responsible Professor (receives feedback)

**Preconditions:** Responsible Professor has shared draft timetable link

**Steps:**
1. Professor opens shared timetable link
2. System displays timetable in week-grid view
3. Professor identifies scheduling issue (e.g., personal conflict, pedagogical concern)
4. Professor adds comment to specific timeslot or overall timetable (e.g., "Martedì 10:00 ho riunione, impossibile")
5. System notifies Responsible Professor of new comment
6. Responsible Professor reads comment, adds corresponding constraint, regenerates timetable
7. System creates "Draft Revision 2" with updated timetable
8. Responsible Professor notifies reviewers of new revision
9. Professor views updated revision, verifies issue resolved

**Success Criteria:**
- Professor can navigate timetable and identify conflicts within 5 minutes
- Comment submission completes within 30 seconds
- Responsible Professor can locate and act on comment within 10 minutes

**Alternative Flows:**
- 4a. Professor approves timetable without comments; Responsible Professor proceeds to finalization

### Journey 3: Student Views Final Timetable

**Actors:** Student

**Preconditions:** Responsible Professor has marked timetable as "Final" and shared public link

**Steps:**
1. Student opens public timetable link (via school website, email, messaging app)
2. System displays finalized timetable in week-grid view
3. Student views class schedule (subject, time, classroom, teacher)
4. Student optionally bookmarks link for future reference

**Success Criteria:**
- Timetable loads within 3 seconds on 4G mobile connection
- Timetable readable on smartphone screen without horizontal scrolling
- Student can identify specific class information within 10 seconds

**Alternative Flows:**
- 1a. Student attempts to access draft or constraint data via URL manipulation; system returns 404 or redirects to final timetable only

## Domain Requirements

**DR-1: Italian School Week Structure**
- Support standard Italian school week: Monday-Saturday, 6 days
- Support short Saturday schedules (typically 4 hours vs. 5-6 on other days)
- Accommodate lyceums and technical institutes with different weekly hour totals (27-32 hours typical range)

**DR-2: Subject Naming and Classification**
- Support Italian subject naming conventions (e.g., "Matematica", "Lingua e Letteratura Italiana", "Scienze Motorie e Sportive")
- Distinguish between theoretical and laboratory hours for technical subjects (e.g., "Chimica" vs. "Laboratorio di Chimica")

**DR-3: Teacher Availability Patterns**
- Support multi-school teachers (docenti condivisi) with availability windows (e.g., "available only Monday/Wednesday at this school")
- Support part-time contracts with hour limits (e.g., 12 hours/week)

**DR-4: Classroom and Resource Constraints**
- Support specialized classroom requirements (laboratories, gyms, computer labs)
- Handle resource conflicts (single gym shared across multiple classes)

**DR-5: Pedagogical Constraints**
- Support maximum consecutive hours per subject (e.g., no more than 2 consecutive math hours)
- Support first/last hour preferences (e.g., physical education not in first hour, heavy subjects in morning)

**DR-6: Data Protection (GDPR Basics)**
- Minimize collection of student personally identifiable information (PII); public timetable view requires no student names
- Secure storage of teacher personal data (names, contact info, availability)
- Provide data export capability for users (Responsible Professor can download all timetable data)
- Support data deletion on request (account and associated timetable removal)

**DR-7: Localization**
- User interface in Italian language only (MVP)
- Date formatting in DD/MM/YYYY (Italian standard)
- Time formatting in 24-hour clock (HH:MM)

## Innovation Analysis

### Competitive Landscape

**Existing Solutions:**
- **Manual spreadsheet-based timetabling**: High error rate, time-intensive, no constraint validation
- **Commercial timetabling software** (e.g., Orario Facile, GP-Untis): Form-based constraint input requiring technical knowledge; steep learning curve; expensive licensing
- **Generic constraint solvers** (e.g., OptaPlanner, Timefold): Require programming expertise; no pre-built education domain model

**Market Gap:** No accessible, domain-aware timetabling tool for non-technical Italian school administrators that accepts natural language input.

### LLM + Constraint Solver Approach

1. User inputs scheduling rules in natural language Italian
2. LLM translates natural language to structured constraint representation
3. System validates and displays interpreted constraints to user for confirmation
4. Constraint solver processes formal constraints and generates timetable satisfying all requirements
5. System presents timetable to user in human-readable format

**Advantages:**
- **Accessibility:** Eliminates need for technical constraint syntax knowledge
- **Flexibility:** Supports arbitrary constraint complexity expressible in natural language
- **Transparency:** User can review and correct LLM interpretation before solving
- **Separation of concerns:** LLM handles ambiguity and language understanding; solver guarantees mathematical correctness

### Risks and Mitigation

- **LLM misinterprets constraint intent** → Display interpreted constraints for explicit user confirmation; allow manual correction
- **LLM generates invalid constraint representation** → Schema validation rejects malformed constraints; prompt user to rephrase
- **LLM API unavailable or rate-limited** → Request queuing and retry logic; provide manual fallback (structured form input)
- **Unsolvable constraint sets** → Conflict explanation in natural language when solve fails; suggest constraint relaxation

## Functional Requirements

### Constraint Input and Management

**FR-1: Natural Language Constraint Input** (MUST)
- System accepts constraint input in Italian natural language via multi-line text field
- Supports constraint types: teacher availability, subject scheduling preferences, resource allocation, consecutive hour limits
- **Acceptance Criteria:** Text field accepts ≥500 characters per constraint; user can submit ≥10 constraints per timetable
- **Traceability:** Journey 1, Step 4

**FR-2: Constraint Translation and Verification** (MUST)
- System translates natural language constraints to formal representation using configured LLM endpoint
- System displays translated constraints in human-readable format for user verification
- User can approve, edit, or reject translated constraints before solving
- **Acceptance Criteria:** Translation completes within 10 seconds per constraint (P95); system displays constraint type, affected entities, and restriction in Italian
- **Traceability:** Journey 1, Steps 5-6

**FR-3: Constraint Conflict Detection** (SHOULD)
- System detects obvious constraint conflicts before solving (e.g., teacher double-booked, hour totals exceed capacity)
- **Acceptance Criteria:** Identifies conflicting teacher assignments and hour-total mismatches with 100% accuracy; warning identifies conflicting constraints by description

**FR-4: Constraint Library Management** (COULD)
- User can save constraint sets as reusable templates and apply them to new timetables
- **Acceptance Criteria:** User can name, save, browse, and apply constraint templates

### Timetable Generation

**FR-5: Single-Class Timetable Generation** (MUST)
- System generates timetable satisfying all user-defined constraints for a single class section
- Supports 6-day structure (Monday-Saturday) and 27-32 weekly hour slots
- **Acceptance Criteria:** All required subject hours assigned; zero MUST constraints violated; generation completes within 5 minutes for ≤20 constraints
- **Traceability:** Journey 1, Step 8; SC-3

**FR-6: Timetable Regeneration** (MUST)
- User can modify constraints and regenerate timetable, creating new revision while preserving previous ones
- **Acceptance Criteria:** Regeneration completes within 10 minutes; previous revision remains accessible; revision number increments automatically
- **Traceability:** Journey 2, Steps 6-7; SC-5

**FR-7: Unsolvable Constraint Handling** (MUST)
- System detects when constraint set has no valid solution and provides conflict explanation
- **Acceptance Criteria:** Returns unsolvable status within 5 minutes; identifies ≥1 conflicting constraint pair; user can return to editing without data loss
- **Traceability:** Journey 1, Alternative Flow 8a

### Timetable Visualization and Sharing

**FR-8: Week-Grid Timetable View** (MUST)
- Displays timetable in week-grid format (rows = time slots, columns = days) with subject, teacher, and classroom per cell
- **Acceptance Criteria:** Renders correctly on desktop and mobile browsers (≥360px viewport); readable without zooming on mobile
- **Traceability:** Journey 2, Step 2; Journey 3, Steps 2-3

**FR-9: Timetable Sharing via Link** (MUST)
- Generates unique shareable URL for each revision; draft links require authentication; final links are public
- **Acceptance Criteria:** URL generation <2 seconds; unauthenticated users denied access to drafts; unauthenticated users can view final timetables
- **Traceability:** Journey 1, Step 10; Journey 3, Step 1

**FR-10: Comment System** (MUST)
- Professors can add comments referencing specific timeslots or the overall timetable; Responsible Professor receives notification
- **Acceptance Criteria:** Comment submission <5 seconds; displays author, timestamp, referenced timeslot; notification within 1 minute
- **Traceability:** Journey 2, Steps 4-5

### User and Access Management

**FR-11: User Authentication** (MUST)
- Email/password authentication for Responsible Professor and Professor roles
- **Acceptance Criteria:** Registration with email + password (≥8 characters); session persists ≥24 hours

**FR-12: Role-Based Access Control** (MUST)
- Enforces permissions: Responsible Professor (full access), Professor (read + comment), Public (final view only)
- **Acceptance Criteria:** Professor users receive 403 on edit/delete attempts; unauthenticated users receive 401 on draft access
- **Traceability:** Journey 3, Alternative Flow 1a

**FR-13: LLM Endpoint Configuration** (MUST)
- Responsible Professor configures LLM API endpoint (URL, API key, model identifier) via settings page
- **Acceptance Criteria:** Accepts OpenAI-compatible API base URL; validates connectivity with test request before saving; configuration persists across sessions

### Timetable Lifecycle Management

**FR-14: Timetable Finalization** (MUST)
- Responsible Professor marks revision as "Final"; timetable becomes publicly accessible and immutable
- **Acceptance Criteria:** Single-action status change; public link active within 10 seconds; constraint modification prevented after finalization
- **Traceability:** Journey 3, Precondition

**FR-15: Timetable Deletion** (SHOULD)
- Draft timetables can be deleted; finalized timetables are archived instead
- **Acceptance Criteria:** Deletion via confirmation dialog; finalized timetables moved to archive; deletion completes within 1 hour

**FR-16: Revision History** (SHOULD)
- System maintains history of all revisions with timestamps; user can view previous revisions and their constraints
- **Acceptance Criteria:** Stores ≥10 revisions per timetable; user can select and view any previous revision

## Non-Functional Requirements

### Performance

**NFR-1: Timetable Generation Latency** (MUST)
- P95 generation time ≤5 minutes for ≤20 constraints; P95 regeneration time ≤10 minutes
- Measurement: Server-side elapsed time from solve initiation to result

**NFR-2: Page Load Time** (MUST)
- P95 page load time ≤3 seconds on 4G mobile connection (10 Mbps, 50ms latency)
- Measurement: Time to First Contentful Paint via browser performance API

**NFR-3: LLM Translation Latency** (MUST)
- P95 constraint translation time ≤10 seconds per constraint
- Measurement: Round-trip time from API request to parsed response

**NFR-4: Concurrent User Capacity** (SHOULD)
- Supports ≥10 concurrent users and ≥3 simultaneous generation operations without degrading NFR-1/NFR-2
- Measurement: Load testing with 10 concurrent sessions

### Security

**NFR-5: Authentication Security** (MUST)
- Passwords hashed using bcrypt or Argon2 (minimum work factor 12); HTTPS enforced in production
- Measurement: Code review; SSL Labs scan A- minimum

**NFR-6: Authorization Enforcement** (MUST)
- User permissions validated on every API request; draft timetables and constraints inaccessible to unauthenticated users
- Measurement: Penetration testing confirms zero authorization bypass

**NFR-7: API Key Protection** (MUST)
- LLM API keys encrypted at rest (AES-256); never logged or exposed in error messages
- Measurement: Code review; log audit confirms zero key exposure

**NFR-8: Data Privacy** (MUST)
- Minimal PII collection; no student identifiers required; data export (JSON) and account deletion supported on request
- Measurement: Data model review; manual test of export and deletion

### Usability

**NFR-9: Mobile Responsiveness** (MUST)
- UI renders correctly from 360px (mobile) to 1920px (desktop); timetable readable without horizontal scrolling on mobile
- Measurement: Manual testing on iPhone SE (375px), iPad (768px), desktop (1920px)

**NFR-10: Italian Language Interface** (MUST)
- All user-facing text in Italian; dates DD/MM/YYYY; times 24-hour clock
- Measurement: UI audit confirms zero English text in user-facing components

**NFR-11: Constraint Input Usability** (MUST)
- Constraint input requires no technical or programming knowledge; verification display uses plain Italian
- Measurement: Usability testing with ≥3 non-technical users; ≥80% task completion without assistance

### Reliability

**NFR-12: System Availability** (SHOULD)
- ≥95% uptime during peak usage (August-September, school year planning)
- Measurement: Uptime monitoring over 60-day peak window

**NFR-13: Data Persistence** (MUST)
- Timetable data and constraints persist across server restarts; zero data loss under normal shutdown
- Measurement: Database transaction logging; graceful shutdown test

**NFR-14: Error Handling** (MUST)
- User-friendly error messages in Italian for common failures (LLM unavailable, unsolvable constraints, timeout); detailed server-side logging
- Measurement: Error scenario testing; server logs contain stack traces

### Maintainability

**NFR-15: Code Documentation** (SHOULD)
- Critical functions (constraint translation, solver invocation) include inline comments; system architecture documented
- Measurement: Code review; architecture documentation exists

**NFR-16: Dependency Management** (SHOULD)
- All external dependencies declared with version pinning; ≤3 runtime dependencies for core solver functionality
- Measurement: Package manifest review confirms version pins and dependency count
