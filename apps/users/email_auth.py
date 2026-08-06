import secrets
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

CODE_LENGTH = 6
CODE_EXPIRY_MINUTES = 10


class EmailAuthCode(models.Model):
    class Purpose(models.TextChoices):
        LOGIN = "login", "Login"
        PASSWORD_RESET = "password_reset", "Password reset"

    challenge_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_auth_codes",
    )
    code = models.CharField(max_length=CODE_LENGTH)
    purpose = models.CharField(max_length=32, choices=Purpose.choices)
    expiration_date = models.DateTimeField()
    validated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "users"
        ordering = ["-expiration_date"]
        indexes = [
            models.Index(fields=["user", "purpose", "validated_at"]),
        ]

    def __str__(self):
        return f"{self.purpose}:{self.user_id}:{self.challenge_id}"

    @property
    def has_expired(self) -> bool:
        return self.expiration_date < timezone.now()

    @classmethod
    def create_code(cls, *, user, purpose: str) -> "EmailAuthCode":
        cls.objects.filter(
            user=user,
            purpose=purpose,
            validated_at__isnull=True,
        ).delete()

        code = "".join(secrets.choice("0123456789") for _ in range(CODE_LENGTH))
        return cls.objects.create(
            user=user,
            code=code,
            purpose=purpose,
            expiration_date=timezone.now()
            + timezone.timedelta(minutes=CODE_EXPIRY_MINUTES),
        )
