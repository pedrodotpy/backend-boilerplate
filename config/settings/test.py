import os

# Isolate tests from local .env secrets; DB comes from DATABASE_URL (Postgres in Compose).
os.environ.setdefault("SECRET_KEY", "test-insecure-secret-key-for-pytest-only")
os.environ.setdefault(
    "DATABASE_URL",
    "postgres://postgres:postgres@db:5432/app",
)

from .base import *  # noqa: E402, F403

DEBUG = False
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
LOGIN_2FA_ENABLED = False

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
