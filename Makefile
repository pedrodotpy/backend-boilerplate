.PHONY: migrate makemigrations schema test run run-2fa up worker createsuperuser seed-e2e build

COMPOSE ?= docker compose
BACKEND = $(COMPOSE) run --rm backend

build:
	$(COMPOSE) build

migrate:
	$(BACKEND) uv run python manage.py migrate

makemigrations:
	$(BACKEND) uv run python manage.py makemigrations

schema:
	$(BACKEND) uv run python manage.py spectacular --file schema.yml

test:
	$(BACKEND) uv run pytest

up:
	$(COMPOSE) up db redis backend worker

run:
	$(COMPOSE) up db redis backend

run-2fa:
	LOGIN_2FA_ENABLED=True $(COMPOSE) up db redis backend

worker:
	$(COMPOSE) up worker

createsuperuser:
	$(BACKEND) uv run python manage.py createsuperuser

seed-e2e:
	$(BACKEND) uv run python manage.py seed_e2e --extra-users 15
