import pytest
from rest_framework import status

from apps.users.tests.conftest import TEST_PASSWORD, grant_user_perms

pytestmark = pytest.mark.django_db


class TestTokenObtain:
    def test_token_obtain_with_email(self, api_client, superuser):
        response = api_client.post(
            "/api/v1/auth/token/",
            {"email": superuser.email, "password": TEST_PASSWORD},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data

    def test_token_obtain_bad_password(self, api_client, superuser):
        response = api_client.post(
            "/api/v1/auth/token/",
            {"email": superuser.email, "password": "wrong-password"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_token_obtain_missing_fields(self, api_client):
        response = api_client.post("/api/v1/auth/token/", {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestTokenRefresh:
    def test_refresh_returns_new_access(self, api_client, superuser):
        obtain = api_client.post(
            "/api/v1/auth/token/",
            {"email": superuser.email, "password": TEST_PASSWORD},
            format="json",
        )
        refresh = obtain.data["refresh"]

        response = api_client.post(
            "/api/v1/auth/token/refresh/",
            {"refresh": refresh},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        # ROTATE_REFRESH_TOKENS=True → new refresh token issued
        assert "refresh" in response.data
        assert response.data["refresh"] != refresh

    def test_refresh_with_invalid_token(self, api_client):
        response = api_client.post(
            "/api/v1/auth/token/refresh/",
            {"refresh": "not-a-valid-token"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestLogout:
    def test_logout_blacklists_refresh(self, api_client, superuser, auth_as):
        obtain = api_client.post(
            "/api/v1/auth/token/",
            {"email": superuser.email, "password": TEST_PASSWORD},
            format="json",
        )
        access = obtain.data["access"]
        refresh = obtain.data["refresh"]

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        response = api_client.post(
            "/api/v1/auth/logout/",
            {"refresh": refresh},
            format="json",
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

        reuse = api_client.post(
            "/api/v1/auth/token/refresh/",
            {"refresh": refresh},
            format="json",
        )
        assert reuse.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout_invalid_refresh(self, api_client, superuser, auth_as):
        auth_as(superuser)
        response = api_client.post(
            "/api/v1/auth/logout/",
            {"refresh": "not-a-valid-token"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_logout_requires_auth(self, api_client):
        response = api_client.post(
            "/api/v1/auth/logout/",
            {"refresh": "anything"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestMe:
    def test_me_returns_permissions(self, api_client, superuser, auth_as):
        auth_as(superuser)
        response = api_client.get("/api/v1/auth/me/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == superuser.email
        assert "users.view_user" in response.data["permissions"]

    def test_me_returns_subset_for_permissioned_user(self, api_client, user, auth_as):
        grant_user_perms(user, "view_user")
        auth_as(user)
        response = api_client.get("/api/v1/auth/me/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == user.email
        assert "users.view_user" in response.data["permissions"]
        assert "users.add_user" not in response.data["permissions"]

    def test_me_requires_auth(self, api_client):
        response = api_client.get("/api/v1/auth/me/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
