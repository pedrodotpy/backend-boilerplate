from celery import shared_task

from apps.email_server.models import SMTPServer


@shared_task
def send_mail_task(
    subject,
    to,
    template=None,
    message=None,
    context=None,
    reply_to=None,
):
    """Deliver mail via the configured SMTPServer (sync send_mail)."""
    SMTPServer.objects.get_current().send_mail(
        subject=subject,
        to=to,
        template=template,
        message=message,
        context=context or {},
        reply_to=reply_to,
    )


def queue_mail(subject, to, **kwargs):
    """Enqueue send_mail_task. Prefer this over calling send_mail from request handlers."""
    return send_mail_task.delay(
        subject,
        to,
        template=kwargs.get("template"),
        message=kwargs.get("message"),
        context=kwargs.get("context"),
        reply_to=kwargs.get("reply_to"),
    )
