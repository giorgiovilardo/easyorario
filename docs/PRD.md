# Easyorario

Easyorario is a simple but useful application that, using the Z3 Constraint Solver,
helps italian professors in determining the hours table when starting a new school year.

The differentiator is that we use an LLM loop to derive the constraints to load into Z3,
so the professors (which are not technical) can insert the rules with natural language.

## What is in scope

- Single class hour table derivation
- Web UI
- Bring your own LLM (via config page, url for the openapi compatible stuff)
- Hour table revisions

## What is not in scope

- Multiclass hour table

## Personas

- Professor
  - User of the system, view only role. Can see a hour table and leave a comments on a revision
- Responsible professor
  - Admin of the system, can start creating a hour table and specify the constraints.
- Student
  - Can only view a hour table marked as final.
  - Can never see the generating constraints.
  - Delicate role; might be better to not let them log in for the first iteration.
