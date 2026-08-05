import pytest
from django.contrib.auth import get_user_model
from rest_framework import status

from apps.users.tests.conftest import TEST_PASSWORD, grant_user_perms

User = get_user_model()

pytestmark = pytest.mark.django_db


class TestUsersList:
    def test_anonymous_cannot_list_users(self, api_client):
        response = api_client.get("/api/v1/users/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_users_list_requires_view_permission(self, api_client, user, auth_as):
        auth_as(user)
        response = api_client.get("/api/v1/users/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

        grant_user_perms(user, "view_user")
        auth_as(user)
        response = api_client.get("/api/v1/users/")
        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data

    def test_users_list_pagination(self, api_client, superuser, auth_as):
        for i in range(5):
            User.objects.create_user(
                email=f"page{i}@example.com",
                password=TEST_PASSWORD,
            )
        auth_as(superuser)
        response = api_client.get("/api/v1/users/?limit=2&offset=0")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 2
        assert response.data["count"] >= 5
        assert response.data["next"] is not None

        response2 = api_client.get("/api/v1/users/?limit=2&offset=2")
        assert response2.status_code == status.HTTP_200_OK
        assert len(response2.data["results"]) == 2
        emails_page1 = {u["email"] for u in response.data["results"]}
        emails_page2 = {u["email"] for u in response2.data["results"]}
        assert emails_page1.isdisjoint(emails_page2)

    def test_users_list_search(self, api_client, superuser, auth_as):
        User.objects.create_user(email="findme@example.com", password=TEST_PASSWORD)
        User.objects.create_user(email="other@example.com", password=TEST_PASSWORD)
        auth_as(superuser)
        response = api_client.get("/api/v1/users/?search=findme")
        assert response.status_code == status.HTTP_200_OK
        emails = [u["email"] for u in response.data["results"]]
        assert "findme@example.com" in emails
        assert "other@example.com" not in emails

    def test_users_list_ordering(self, api_client, superuser, auth_as):
        User.objects.create_user(email="aaa@example.com", password=TEST_PASSWORD)
        User.objects.create_user(email="zzz@example.com", password=TEST_PASSWORD)
        auth_as(superuser)

        asc = api_client.get("/api/v1/users/?ordering=email")
        assert asc.status_code == status.HTTP_200_OK
        asc_emails = [u["email"] for u in asc.data["results"]]
        assert asc_emails == sorted(asc_emails)

        desc = api_client.get("/api/v1/users/?ordering=-email")
        assert desc.status_code == status.HTTP_200_OK
        desc_emails = [u["email"] for u in desc.data["results"]]
        assert desc_emails == sorted(desc_emails, reverse=True)


class TestUsersCreate:
    def test_users_create_requires_add_permission(self, api_client, user, auth_as):
        grant_user_perms(user, "view_user")
        auth_as(user)
        response = api_client.post(
            "/api/v1/users/",
            {"email": "new@example.com", "password": "newpass123"},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_users_create_as_superuser(self, api_client, superuser, auth_as):
        auth_as(superuser)
        response = api_client.post(
            "/api/v1/users/",
            {"email": "new@example.com", "password": "newpass123"},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["email"] == "new@example.com"

    def test_users_create_duplicate_email(self, api_client, superuser, auth_as):
        auth_as(superuser)
        response = api_client.post(
            "/api/v1/users/",
            {"email": superuser.email, "password": "newpass123"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_users_create_short_password(self, api_client, superuser, auth_as):
        auth_as(superuser)
        response = api_client.post(
            "/api/v1/users/",
            {"email": "short@example.com", "password": "short"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestUsersRetrieve:
    def test_retrieve_requires_view(self, api_client, user, superuser, auth_as):
        auth_as(user)
        response = api_client.get(f"/api/v1/users/{superuser.id}/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

        grant_user_perms(user, "view_user")
        auth_as(user)
        response = api_client.get(f"/api/v1/users/{superuser.id}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == superuser.email

    def test_retrieve_not_found(self, api_client, superuser, auth_as):
        auth_as(superuser)
        response = api_client.get("/api/v1/users/999999/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_anonymous(self, api_client, superuser):
        response = api_client.get(f"/api/v1/users/{superuser.id}/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestUsersUpdate:
    def test_update_requires_change_permission(self, api_client, user, auth_as):
        grant_user_perms(user, "view_user")
        auth_as(user)
        target = User.objects.create_user(
            email="target@example.com",
            password=TEST_PASSWORD,
        )
        response = api_client.patch(
            f"/api/v1/users/{target.id}/",
            {"email": "renamed@example.com"},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_partial_update_as_superuser(self, api_client, superuser, auth_as):
        target = User.objects.create_user(
            email="target@example.com",
            password=TEST_PASSWORD,
        )
        auth_as(superuser)
        response = api_client.patch(
            f"/api/v1/users/{target.id}/",
            {"email": "renamed@example.com", "is_staff": True},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == "renamed@example.com"
        assert response.data["is_staff"] is True

    def test_update_password(self, api_client, superuser, auth_as):
        target = User.objects.create_user(
            email="pwd@example.com",
            password=TEST_PASSWORD,
        )
        auth_as(superuser)
        response = api_client.patch(
            f"/api/v1/users/{target.id}/",
            {"password": "brandnewpass99"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        target.refresh_from_db()
        assert target.check_password("brandnewpass99")


class TestUsersDestroy:
    def test_delete_requires_delete_permission(self, api_client, user, auth_as):
        grant_user_perms(user, "view_user", "change_user")
        auth_as(user)
        target = User.objects.create_user(
            email="doomed@example.com",
            password=TEST_PASSWORD,
        )
        response = api_client.delete(f"/api/v1/users/{target.id}/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_as_superuser(self, api_client, superuser, auth_as):
        target = User.objects.create_user(
            email="doomed@example.com",
            password=TEST_PASSWORD,
        )
        auth_as(superuser)
        response = api_client.delete(f"/api/v1/users/{target.id}/")
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not User.objects.filter(pk=target.pk).exists()
