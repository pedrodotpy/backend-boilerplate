from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import update_last_login
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import status, viewsets
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.users.api.permissions import DjangoModelPermissionsWithView
from apps.users.api.serializers import (
    ChallengeRequiredSerializer,
    EmailTokenObtainSerializer,
    ForgotPasswordSerializer,
    LogoutSerializer,
    MeSerializer,
    ResendCodeSerializer,
    ResetPasswordSerializer,
    TokenPairSerializer,
    UserCreateSerializer,
    UserSerializer,
    UserUpdateSerializer,
    VerifyCodeSerializer,
)
from apps.users.auth_codes import censor_email, create_and_send_auth_code
from apps.users.email_auth import EmailAuthCode

User = get_user_model()


def _tokens_for_user(user) -> dict:
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


class EmailTokenObtainPairView(TokenObtainPairView):
    """JWT obtain using email + password. May return a 2FA challenge instead."""

    permission_classes = [AllowAny]
    serializer_class = EmailTokenObtainSerializer

    def get_serializer(self, *args, **kwargs):
        kwargs["defer_tokens"] = settings.LOGIN_2FA_ENABLED
        return super().get_serializer(*args, **kwargs)

    @extend_schema(
        request=EmailTokenObtainSerializer,
        responses={
            200: OpenApiResponse(
                response=TokenPairSerializer,
                description="JWT pair when LOGIN_2FA_ENABLED is false.",
            ),
            202: OpenApiResponse(
                response=ChallengeRequiredSerializer,
                description="2FA challenge when LOGIN_2FA_ENABLED is true.",
            ),
        },
        examples=[
            OpenApiExample(
                "JWT pair",
                value={"access": "...", "refresh": "..."},
                response_only=True,
                status_codes=["200"],
            ),
            OpenApiExample(
                "2FA challenge",
                value={
                    "challenge_id": "00000000-0000-0000-0000-000000000001",
                    "destination": "u***@example.com",
                },
                response_only=True,
                status_codes=["202"],
            ),
        ],
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.user

        if settings.LOGIN_2FA_ENABLED:
            auth_code = create_and_send_auth_code(
                user=user,
                purpose=EmailAuthCode.Purpose.LOGIN,
            )
            return Response(
                {
                    "challenge_id": str(auth_code.challenge_id),
                    "destination": censor_email(user.email),
                },
                status=status.HTTP_202_ACCEPTED,
            )

        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class EmailTokenRefreshView(TokenRefreshView):
    permission_classes = [AllowAny]


class VerifyCodeView(APIView):
    permission_classes = [AllowAny]
    serializer_class = VerifyCodeSerializer

    @extend_schema(
        request=VerifyCodeSerializer,
        responses={200: TokenPairSerializer},
    )
    def post(self, request):
        serializer = VerifyCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        auth_code = serializer.validated_data["auth_code"]
        auth_code.validated_at = timezone.now()
        auth_code.save(update_fields=["validated_at"])
        if api_settings.UPDATE_LAST_LOGIN:
            update_last_login(None, auth_code.user)
        return Response(_tokens_for_user(auth_code.user), status=status.HTTP_200_OK)


class ResendCodeView(APIView):
    permission_classes = [AllowAny]
    serializer_class = ResendCodeSerializer

    @extend_schema(
        request=ResendCodeSerializer,
        responses={200: ChallengeRequiredSerializer},
    )
    def post(self, request):
        serializer = ResendCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        previous = serializer.validated_data["challenge_id"]
        auth_code = create_and_send_auth_code(
            user=previous.user,
            purpose=previous.purpose,
        )
        return Response(
            {
                "challenge_id": str(auth_code.challenge_id),
                "destination": censor_email(previous.user.email),
            },
            status=status.HTTP_200_OK,
        )


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]
    serializer_class = ForgotPasswordSerializer

    @extend_schema(
        request=ForgotPasswordSerializer,
        responses={204: OpenApiResponse(description="Always empty (anti-enumeration).")},
    )
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user is not None:
            create_and_send_auth_code(
                user=user,
                purpose=EmailAuthCode.Purpose.PASSWORD_RESET,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]
    serializer_class = ResetPasswordSerializer

    @extend_schema(
        request=ResetPasswordSerializer,
        responses={204: OpenApiResponse(description="Password updated.")},
    )
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        auth_code = serializer.validated_data["auth_code"]
        new_password = serializer.validated_data["new_password"]

        try:
            validate_password(new_password, user=user)
        except DjangoValidationError as exc:
            return Response(
                {"new_password": list(exc.messages)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save(update_fields=["password"])
        auth_code.validated_at = timezone.now()
        auth_code.save(update_fields=["validated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = LogoutSerializer

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            token = RefreshToken(serializer.validated_data["refresh"])
            token.blacklist()
        except Exception:
            return Response(
                {"detail": "Invalid or expired refresh token."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MeSerializer

    def get_object(self):
        return self.request.user


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by("email")
    permission_classes = [IsAuthenticated, DjangoModelPermissionsWithView]
    search_fields = ["email"]
    ordering_fields = ["email", "created", "modified", "last_login"]
    ordering = ["email"]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        if self.action in ("update", "partial_update"):
            return UserUpdateSerializer
        return UserSerializer
