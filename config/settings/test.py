import os

# Isolate tests from local .env database / secrets.
os.environ.setdefault("SECRET_KEY", "test-insecure-secret-key-for-pytest-only")
os.environ["DATABASE_URL"] = "sqlite://:memory:"

from .base import *  # noqa: E402, F403

DEBUG = False
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
