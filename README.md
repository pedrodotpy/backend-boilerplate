# Django Boilerplate

Login-gated Django REST API with JWT, custom email `User`, DRF, and OpenAPI (`drf-spectacular`).

Companion frontend: `../react-boilerplate`. Shared SPECS: `../fullstack-bootstrap/specs/`.

**Docker-first:** Postgres, the API, and pytest all run via Docker Compose. Make wraps Compose.

## Setup

```bash
cp .env.example .env
cp config/settings/local.py.example config/settings/local.py
make build
make migrate
make createsuperuser
make run
```

API: `http://localhost:8000`.

## Common commands

```bash
make migrate
make makemigrations
make schema          # writes schema.yml for the React OpenAPI client
make test            # pytest API E2E (Postgres via Compose)
make seed-e2e        # users for React Playwright (admin + viewer + extras)
make run
```

Add dependencies inside the container:

```bash
docker compose run --rm backend uv add <pkg>
docker compose run --rm backend uv add --dev <pkg>
```

## Testing

API coverage is **end-to-end through DRF** (`apps/*/tests/`). Prefer expanding those over model/serializer unit tests for the same paths. New/changed API behavior **must** ship with matching pytest coverage.

```bash
make test
```

`config/settings/test.py` uses the Compose Postgres `DATABASE_URL`; pytest-django creates `test_app`. Do not use SQLite for tests.

For the React Playwright suite, use the frontend’s Compose E2E targets (`make test-e2e` / `make test-e2e-2fa` in `react-boilerplate`), or seed and run the API alone:

```bash
make seed-e2e
make run          # LOGIN_2FA_ENABLED=False (default)
# or: make run-2fa   # for frontend make test-e2e-2fa
```

Seeded accounts (password `e2epass123`):

- `e2e-admin@example.com` — superuser
- `e2e-viewer@example.com` — `users.view_user` only

## Agent rules

See `AGENTS.md` and `../fullstack-bootstrap/specs/05-agent-conventions.md`.
Use `uv add` / `manage.py` via Compose — do not hand-edit migrations or lockfiles when the CLI works.
