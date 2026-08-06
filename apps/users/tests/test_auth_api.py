import pytest
from django.core import mail
from django.utils import timezone
from rest_framework import status

from apps.users.email_auth import EmailAuthCode
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

    def test_token_obtain_rejects_inactive_user(self, api_client, user, password):
        user.is_active = False
        user.save(update_fields=["is_active"])
        response = api_client.post(
            "/api/v1/auth/token/",
            {"email": user.email, "password": password},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestLogin2FA:
    def test_token_returns_challenge_when_2fa_enabled(
        self, api_client, superuser, settings
    ):
        settings.LOGIN_2FA_ENABLED = True
        response = api_client.post(
            "/api/v1/auth/token/",
            {"email": superuser.email, "password": TEST_PASSWORD},
            format="json",
        )
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert "challenge_id" in response.data
        assert "destination" in response.data
        assert "access" not in response.data
        assert len(mail.outbox) == 1
        auth_code = EmailAuthCode.objects.get(challenge_id=response.data["challenge_id"])
        assert auth_code.purpose == EmailAuthCode.Purpose.LOGIN
        assert auth_code.code in mail.outbox[0].alternatives[0][0]

    def test_verify_code_returns_tokens(self, api_client, superuser, settings):
        settings.LOGIN_2FA_ENABLED = True
        challenge = api_client.post(
            "/api/v1/auth/token/",
            {"email": superuser.email, "password": TEST_PASSWORD},
            format="json",
        )
        auth_code = EmailAuthCode.objects.get(
            challenge_id=challenge.data["challenge_id"]
        )
        response = api_client.post(
            "/api/v1/auth/verify-code/",
            {
                "challenge_id": str(auth_code.challenge_id),
                "code": auth_code.code,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data
        auth_code.refresh_from_db()
        assert auth_code.validated_at is not None

    def test_verify_code_rejects_wrong_code(self, api_client, superuser, settings):
        settings.LOGIN_2FA_ENABLED = True
        challenge = api_client.post(
            "/api/v1/auth/token/",
            {"email": superuser.email, "password": TEST_PASSWORD},
            format="json",
        )
        response = api_client.post(
            "/api/v1/auth/verify-code/",
            {
                "challenge_id": challenge.data["challenge_id"],
                "code": "000000",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_verify_code_rejects_expired(self, api_client, superuser, settings):
        settings.LOGIN_2FA_ENABLED = True
        challenge = api_client.post(
            "/api/v1/auth/token/",
            {"email": superuser.email, "password": TEST_PASSWORD},
            format="json",
        )
        auth_code = EmailAuthCode.objects.get(
            challenge_id=challenge.data["challenge_id"]
        )
        auth_code.expiration_date = timezone.now() - timezone.timedelta(minutes=1)
        auth_code.save(update_fields=["expiration_date"])
        response = api_client.post(
            "/api/v1/auth/verify-code/",
            {
                "challenge_id": str(auth_code.challenge_id),
                "code": auth_code.code,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_resend_code_issues_new_challenge(self, api_client, superuser, settings):
        settings.LOGIN_2FA_ENABLED = True
        challenge = api_client.post(
            "/api/v1/auth/token/",
            {"email": superuser.email, "password": TEST_PASSWORD},
            format="json",
        )
        old_id = challenge.data["challenge_id"]
        response = api_client.post(
            "/api/v1/auth/resend-code/",
            {"challenge_id": old_id},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["challenge_id"] != old_id
        assert len(mail.outbox) == 2
        assert not EmailAuthCode.objects.filter(
            challenge_id=old_id, validated_at__isnull=True
        ).exists()

    def test_verify_code_rejects_unknown_challenge_id(self, api_client, settings):
        settings.LOGIN_2FA_ENABLED = True
        response = api_client.post(
            "/api/v1/auth/verify-code/",
            {
                "challenge_id": "00000000-0000-0000-0000-000000000099",
                "code": "123456",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_verify_code_requires_challenge_id(self, api_client, settings):
        settings.LOGIN_2FA_ENABLED = True
        response = api_client.post(
            "/api/v1/auth/verify-code/",
            {"code": "123456"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_resend_code_rejects_unknown_challenge_id(self, api_client, settings):
        settings.LOGIN_2FA_ENABLED = True
        response = api_client.post(
            "/api/v1/auth/resend-code/",
            {"challenge_id": "00000000-0000-0000-0000-000000000099"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestForgotResetPassword:
    def test_forgot_password_always_204_even_unknown(self, api_client):
        response = api_client.post(
            "/api/v1/auth/forgot-password/",
            {"email": "nobody@example.com"},
            format="json",
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert len(mail.outbox) == 0

    def test_forgot_password_sends_code_for_existing_user(self, api_client, user):
        response = api_client.post(
            "/api/v1/auth/forgot-password/",
            {"email": user.email},
            format="json",
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert len(mail.outbox) == 1
        assert EmailAuthCode.objects.filter(
            user=user,
            purpose=EmailAuthCode.Purpose.PASSWORD_RESET,
        ).exists()

    def test_forgot_password_skips_inactive_user(self, api_client, user):
        user.is_active = False
        user.save(update_fields=["is_active"])
        response = api_client.post(
            "/api/v1/auth/forgot-password/",
            {"email": user.email},
            format="json",
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert len(mail.outbox) == 0
        assert not EmailAuthCode.objects.filter(user=user).exists()

    def test_reset_password_with_valid_code(self, api_client, user):
        api_client.post(
            "/api/v1/auth/forgot-password/",
            {"email": user.email},
            format="json",
        )
        auth_code = EmailAuthCode.objects.get(
            user=user,
            purpose=EmailAuthCode.Purpose.PASSWORD_RESET,
        )
        new_password = "brand-new-pass-99"
        response = api_client.post(
            "/api/v1/auth/reset-password/",
            {
                "email": user.email,
                "code": auth_code.code,
                "new_password": new_password,
                "confirm_password": new_password,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

        login = api_client.post(
            "/api/v1/auth/token/",
            {"email": user.email, "password": new_password},
            format="json",
        )
        assert login.status_code == status.HTTP_200_OK

    def test_reset_password_rejects_expired_code(self, api_client, user):
        api_client.post(
            "/api/v1/auth/forgot-password/",
            {"email": user.email},
            format="json",
        )
        auth_code = EmailAuthCode.objects.get(
            user=user,
            purpose=EmailAuthCode.Purpose.PASSWORD_RESET,
        )
        auth_code.expiration_date = timezone.now() - timezone.timedelta(minutes=1)
        auth_code.save(update_fields=["expiration_date"])
        response = api_client.post(
            "/api/v1/auth/reset-password/",
            {
                "email": user.email,
                "code": auth_code.code,
                "new_password": "brand-new-pass-99",
                "confirm_password": "brand-new-pass-99",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_reset_password_mismatch(self, api_client, user):
        api_client.post(
            "/api/v1/auth/forgot-password/",
            {"email": user.email},
            format="json",
        )
        auth_code = EmailAuthCode.objects.get(
            user=user,
            purpose=EmailAuthCode.Purpose.PASSWORD_RESET,
        )
        response = api_client.post(
            "/api/v1/auth/reset-password/",
            {
                "email": user.email,
                "code": auth_code.code,
                "new_password": "brand-new-pass-99",
                "confirm_password": "different-pass-99",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_reset_password_rejects_wrong_code(self, api_client, user):
        api_client.post(
            "/api/v1/auth/forgot-password/",
            {"email": user.email},
            format="json",
        )
        response = api_client.post(
            "/api/v1/auth/reset-password/",
            {
                "email": user.email,
                "code": "000000",
                "new_password": "brand-new-pass-99",
                "confirm_password": "brand-new-pass-99",
            },
            format="json",
        )
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
