#!/bin/sh
set -e

if [ ! -f config/settings/local.py ]; then
  cp config/settings/local.py.example config/settings/local.py
fi

if [ ! -f .env ]; then
  cp .env.example .env
fi

# Named volume may be empty on first run; keep lockfile in sync with bind mounts.
uv sync --frozen --no-install-project

exec "$@"
