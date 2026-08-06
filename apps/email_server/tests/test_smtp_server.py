import pytest
from django.core import mail

from apps.email_server.models import SMTPServer
from apps.email_server.tasks import queue_mail, send_mail_task

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


class TestSendMailTask:
    def test_send_mail_task_delivers_via_locmem(self):
        SMTPServer.objects.get_current()
        send_mail_task(
            subject="Task subject",
            to="task@example.com",
            message="<p>From Celery task</p>",
        )
        assert len(mail.outbox) == 1
        assert mail.outbox[0].subject == "Task subject"
        assert mail.outbox[0].to == ["task@example.com"]

    def test_queue_mail_runs_eager_in_tests(self):
        SMTPServer.objects.get_current()
        queue_mail(
            subject="Queued subject",
            to="queued@example.com",
            message="<p>Queued</p>",
        )
        assert len(mail.outbox) == 1
        assert mail.outbox[0].subject == "Queued subject"
