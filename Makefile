.PHONY: migrate makemigrations schema test run createsuperuser seed-e2e

migrate:
	uv run python manage.py migrate

makemigrations:
	uv run python manage.py makemigrations

schema:
	uv run python manage.py spectacular --file schema.yml

test:
	uv run pytest

run:
	uv run python manage.py runserver

createsuperuser:
	uv run python manage.py createsuperuser

seed-e2e:
	uv run python manage.py seed_e2e --extra-users 15
