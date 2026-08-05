# Agent guidelines (django-boilerplate)

- Add dependencies with `uv add` / `uv add --dev` only.
- Schema and apps: `uv run python manage.py makemigrations|migrate|startapp|spectacular|createsuperuser|seed_e2e`.
- Never hand-write migration files or hand-edit `uv.lock` when the CLI can do the job.
- After API changes, run `make schema` and regenerate the React OpenAPI client.
- Keep the API private: only JWT obtain/refresh are anonymous.
- Prefer pytest API E2E (`make test`) over unit tests for the same behavior; update specs when auth/CRUD changes.
- Follow `../fullstack-bootstrap/specs/` especially `04-crud-pattern.md` and `05-agent-conventions.md`.
