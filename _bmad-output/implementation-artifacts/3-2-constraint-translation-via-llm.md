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

- [ ] Task 1 (AC: #)
  - [ ] Subtask 1.1
- [ ] Task 2 (AC: #)
  - [ ] Subtask 2.1

## Dev Notes

- Relevant architecture patterns and constraints
- Source tree components to touch
- Testing standards summary

### Project Structure Notes

- Alignment with unified project structure (paths, modules, naming)
- Detected conflicts or variances (with rationale)

### References

- Cite all technical details with source paths and sections, e.g. [Source: docs/<file>.md#Section]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
