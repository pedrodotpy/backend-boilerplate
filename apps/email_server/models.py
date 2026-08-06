from smtplib import SMTP

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.core.mail.backends.smtp import EmailBackend
from django.db import models
from django.template import loader
from django.utils.translation import gettext_lazy as _


class SMTPServerManager(models.Manager):
    def get_current(self):
        server = self.all().first()
        if server is None:
            server = self.create()
        return server


class SMTPServer(models.Model):
    """Outbound SMTP credentials editable in Django admin."""

    alias = models.CharField(
        _("Alias"),
        max_length=255,
        default="Default",
        help_text=_("Short label for this SMTP configuration."),
    )
    host = models.CharField(
        _("SMTP host"),
        max_length=255,
        default="smtp.gmail.com",
        help_text=_("Example: smtp.gmail.com"),
    )
    port = models.PositiveIntegerField(
        _("Port"),
        default=587,
        help_text=_("SMTP port (typically 587 for TLS or 465 for SSL)."),
    )
    username = models.CharField(
        _("Username"),
        max_length=255,
        blank=True,
        default="",
        help_text=_("Leave blank for an open relay."),
    )
    password = models.CharField(
        _("Password"),
        max_length=255,
        blank=True,
        default="",
        help_text=_("App password or SMTP password."),
    )
    from_email = models.CharField(
        _("From email"),
        max_length=255,
        default="App <noreply@example.com>",
        help_text=_("From header, e.g. App <noreply@example.com>."),
    )
    reply_to = models.CharField(
        _("Reply-To"),
        max_length=255,
        blank=True,
        default="",
        help_text=_("Optional Reply-To address. Defaults to From email."),
    )
    use_tls = models.BooleanField(_("Use TLS"), default=True)
    use_ssl = models.BooleanField(_("Use SSL"), default=False)
    timeout = models.PositiveIntegerField(_("Timeout (seconds)"), blank=True, null=True)

    objects = SMTPServerManager()

    class Meta:
        verbose_name = _("SMTP server")
        verbose_name_plural = _("SMTP servers")

    def __str__(self):
        return self.alias

    def check_connection(self) -> bool:
        try:
            smtp = SMTP(self.host, int(self.port), timeout=self.timeout or 10)
            if self.use_tls:
                smtp.starttls()
            if self.username or self.password:
                smtp.login(self.username, self.password)
            smtp.quit()
        except Exception:
            return False
        return True

    def send_mail(self, subject, to, **kwargs):
        """
        Send an email using this SMTP row when EMAIL_BACKEND is SMTP;
        otherwise honor the configured backend (e.g. filebased in local).

        kwargs:
            template — Django template path (HTML)
            context — template context dict
            message — raw HTML/text body (used when template is omitted)
            reply_to — override Reply-To
        """
        template = kwargs.get("template")
        message = kwargs.get("message")
        context = kwargs.get("context") or {}
        reply_to = kwargs.get("reply_to") or self.reply_to or self.from_email

        if template is None and message is None:
            raise ValueError("Provide either template or message")

        if isinstance(to, str):
            to = [to]

        if template:
            html_body = loader.get_template(template).render(context)
        else:
            html_body = message

        backend_name = (settings.EMAIL_BACKEND or "").lower()
        if backend_name == "django.core.mail.backends.smtp.emailbackend":
            connection = EmailBackend(
                host=self.host,
                port=self.port,
                username=self.username or None,
                password=self.password or None,
                use_tls=self.use_tls,
                use_ssl=self.use_ssl,
                timeout=self.timeout,
                fail_silently=False,
            )
        else:
            connection = get_connection()

        text_fallback = "This email requires an HTML-capable client."
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_fallback,
            from_email=self.from_email,
            to=to,
            headers={"Reply-To": reply_to},
            connection=connection,
        )
        msg.attach_alternative(html_body, "text/html")
        msg.send()
