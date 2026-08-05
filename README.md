# Django Boilerplate

Login-gated Django REST API with JWT, custom email `User`, DRF, and OpenAPI (`drf-spectacular`).

Companion frontend: `../react-boilerplate`. Shared SPECS: `../fullstack-bootstrap/specs/`.

## Setup

```bash
cp .env.example .env
cp config/settings/local.py.example config/settings/local.py
uv sync
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

## Common commands

```bash
make migrate
make makemigrations
make schema          # writes schema.yml for the React OpenAPI client
make test            # pytest API E2E (in-memory SQLite)
make seed-e2e        # users for React Playwright (admin + viewer + extras)
make run
```

## Testing

API coverage is **end-to-end through DRF** (`apps/users/tests/`). Prefer expanding those over model/serializer unit tests for the same paths.

```bash
make test
```

For the React Playwright suite, seed deterministic users then keep the server running:

```bash
make seed-e2e
make run
```

Seeded accounts (password `e2epass123`):

- `e2e-admin@example.com` — superuser
- `e2e-viewer@example.com` — `users.view_user` only

## Agent rules

See `AGENTS.md` and `../fullstack-bootstrap/specs/05-agent-conventions.md`.
Use `uv add` / `manage.py` — do not hand-edit migrations or lockfiles when the CLI works.
