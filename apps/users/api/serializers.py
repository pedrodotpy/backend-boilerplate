from django.contrib.auth.models import update_last_login
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.settings import api_settings

from apps.users.email_auth import EmailAuthCode
from apps.users.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "is_active",
            "is_staff",
            "is_superuser",
            "created",
            "modified",
            "last_login",
        ]
        read_only_fields = [
            "id",
            "is_superuser",
            "created",
            "modified",
            "last_login",
        ]


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "password",
            "is_active",
            "is_staff",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        password = validated_data.pop("password")
        return User.objects.create_user(password=password, **validated_data)


class UserUpdateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, required=False)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "password",
            "is_active",
            "is_staff",
        ]
        read_only_fields = ["id"]

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class MeSerializer(serializers.ModelSerializer):
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "permissions"]

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_permissions(self, obj):
        return sorted(obj.get_all_permissions())


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class EmailTokenObtainSerializer(TokenObtainPairSerializer):
    """Authenticate with email + password; optionally defer JWT for 2FA."""

    def __init__(self, *args, defer_tokens: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.defer_tokens = defer_tokens

    def validate(self, attrs):
        data = super(TokenObtainPairSerializer, self).validate(attrs)
        if self.defer_tokens:
            return data

        refresh = self.get_token(self.user)
        data["refresh"] = str(refresh)
        data["access"] = str(refresh.access_token)

        if api_settings.UPDATE_LAST_LOGIN:
            update_last_login(None, self.user)

        return data


class ChallengeRequiredSerializer(serializers.Serializer):
    challenge_id = serializers.UUIDField()
    destination = serializers.CharField()


class TokenPairSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()


class VerifyCodeSerializer(serializers.Serializer):
    challenge_id = serializers.UUIDField()
    code = serializers.CharField(min_length=6, max_length=6)

    def validate(self, attrs):
        try:
            auth_code = EmailAuthCode.objects.select_related("user").get(
                challenge_id=attrs["challenge_id"],
                purpose=EmailAuthCode.Purpose.LOGIN,
                validated_at__isnull=True,
            )
        except EmailAuthCode.DoesNotExist as exc:
            raise serializers.ValidationError(
                {"non_field_errors": ["Invalid or expired code."]}
            ) from exc

        if auth_code.code != attrs["code"] or auth_code.has_expired:
            raise serializers.ValidationError(
                {"non_field_errors": ["Invalid or expired code."]}
            )

        attrs["auth_code"] = auth_code
        return attrs


class ResendCodeSerializer(serializers.Serializer):
    challenge_id = serializers.UUIDField()

    def validate_challenge_id(self, value):
        try:
            return EmailAuthCode.objects.select_related("user").get(challenge_id=value)
        except EmailAuthCode.DoesNotExist as exc:
            raise serializers.ValidationError("Invalid challenge.") from exc


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(min_length=6, max_length=6)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": ["Passwords do not match."]}
            )

        user = User.objects.filter(email__iexact=attrs["email"]).first()
        if user is None:
            raise serializers.ValidationError(
                {"non_field_errors": ["Invalid or expired code."]}
            )

        auth_code = (
            EmailAuthCode.objects.filter(
                user=user,
                purpose=EmailAuthCode.Purpose.PASSWORD_RESET,
                code=attrs["code"],
                validated_at__isnull=True,
            )
            .order_by("-expiration_date")
            .first()
        )
        if auth_code is None or auth_code.has_expired:
            raise serializers.ValidationError(
                {"non_field_errors": ["Invalid or expired code."]}
            )

        attrs["user"] = user
        attrs["auth_code"] = auth_code
        return attrs
