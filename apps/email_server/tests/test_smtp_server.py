import pytest
from django.core import mail

from apps.email_server.models import SMTPServer

pytestmark = pytest.mark.django_db


class TestSMTPServer:
    def test_get_current_creates_default_row(self):
        assert SMTPServer.objects.count() == 0
        server = SMTPServer.objects.get_current()
        assert server.pk is not None
        assert server.alias == "Default"
        assert SMTPServer.objects.count() == 1
        assert SMTPServer.objects.get_current().pk == server.pk

    def test_send_mail_delivers_via_configured_backend(self):
        server = SMTPServer.objects.get_current()
        server.send_mail(
            subject="Test subject",
            to="recipient@example.com",
            message="<p>Hello from tests</p>",
        )
        assert len(mail.outbox) == 1
        message = mail.outbox[0]
        assert message.subject == "Test subject"
        assert message.to == ["recipient@example.com"]
        assert message.alternatives[0][0] == "<p>Hello from tests</p>"
        assert message.alternatives[0][1] == "text/html"

    def test_send_mail_requires_template_or_message(self):
        server = SMTPServer.objects.get_current()
        with pytest.raises(ValueError, match="template or message"):
            server.send_mail(subject="Empty", to="recipient@example.com")
