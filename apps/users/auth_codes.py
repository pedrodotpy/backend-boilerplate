from django.utils import timezone

from apps.email_server.tasks import queue_mail
from apps.users.email_auth import CODE_EXPIRY_MINUTES, EmailAuthCode


def censor_email(email: str) -> str:
    local, _, domain = email.partition("@")
    if not domain:
        return "***"
    visible = local[:1] if local else "*"
    return f"{visible}***@{domain}"


def create_and_send_auth_code(*, user, purpose: str) -> EmailAuthCode:
    auth_code = EmailAuthCode.create_code(user=user, purpose=purpose)
    expires_at = timezone.localtime(auth_code.expiration_date).strftime(
        "%Y-%m-%d %H:%M:%S %Z"
    )
    subject = (
        "Your login verification code"
        if purpose == EmailAuthCode.Purpose.LOGIN
        else "Your password reset code"
    )
    queue_mail(
        subject=subject,
        to=user.email,
        template="users/email/auth_code.html",
        context={
            "code": auth_code.code,
            "expires_at": expires_at,
            "expiry_minutes": CODE_EXPIRY_MINUTES,
            "purpose": purpose,
        },
    )
    return auth_code
