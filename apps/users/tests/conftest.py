import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

TEST_PASSWORD = "testpass123"


@pytest.fixture
def password():
    return TEST_PASSWORD


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def superuser(password):
    return User.objects.create_superuser(
        email="admin@example.com",
        password=password,
    )


@pytest.fixture
def user(password):
    return User.objects.create_user(
        email="member@example.com",
        password=password,
    )


def grant_user_perms(user, *codenames):
    content_type = ContentType.objects.get_for_model(User)
    for codename in codenames:
        perm = Permission.objects.get(content_type=content_type, codename=codename)
        user.user_permissions.add(perm)
    user = User.objects.get(pk=user.pk)
    return user


def auth_client(client, user):
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client, refresh


@pytest.fixture
def auth_as(api_client):
    def _auth(user):
        return auth_client(api_client, user)

    return _auth
