# Agent guidelines (django-boilerplate)

- Development is **Docker-first**: use Make / `docker compose` (not host `uv run`) for migrate, run, schema, and tests.
- Add dependencies with `docker compose run --rm backend uv add` / `uv add --dev` only.
- Schema and apps: `make migrate|makemigrations|schema|createsuperuser|seed-e2e` or `docker compose run --rm backend uv run python manage.py …`.
- Never hand-write migration files or hand-edit `uv.lock` when the CLI can do the job.
- After API changes, run `make schema` and regenerate the React OpenAPI client.
- Keep the API private: only JWT obtain/refresh (and auth OTP endpoints) are anonymous.
- **Must** add/update pytest API E2E under `apps/<app>/tests/` for new/changed API behavior; leave `make test` green. Do not ask whether tests are wanted.
- Prefer pytest API E2E (`make test`) over unit tests for the same behavior. Tests use Compose Postgres.
- Follow `../fullstack-bootstrap/specs/` especially `04-crud-pattern.md` and `05-agent-conventions.md`.
