# medio-curso-davila

Project following **Spec-Driven Development (SDD)** with a **spec-first** workflow:
no code is written until its specification exists and has been reviewed.

## Workflow

1. **Specify** – Write/update a spec in `specs/` using a template from `specs/_templates/`.
2. **Review** – Spec is reviewed and its status set to `Approved`.
3. **Test** – Derive acceptance tests in `tests/acceptance/` from the spec's acceptance criteria.
4. **Implement** – Write code in `src/` until the tests pass.
5. **Verify** – Confirm implementation matches the spec; update spec status to `Implemented`.

## Structure

```
specs/
  requirements/   High-level product requirements and goals
  features/       Feature specs (behavior, acceptance criteria)
  api/            API contracts (e.g. OpenAPI / interface definitions)
  data/           Data models and schemas
  decisions/      Architecture Decision Records (ADRs)
  _templates/     Templates for new specs
src/              Implementation (written only after specs are approved)
tests/
  acceptance/     Tests derived directly from spec acceptance criteria
  integration/    Integration tests
  unit/           Unit tests
docs/             General documentation
scripts/          Helper scripts
```

## Conventions

- Spec files: `NNN-short-name.md` (e.g. `specs/features/001-user-login.md`).
- Every commit implementing behavior should reference its spec ID.
- If the behavior changes, update the spec **first**, then tests, then code.
