from django.contrib import admin, messages
from django.utils.translation import gettext_lazy as _

from apps.email_server.models import SMTPServer


@admin.register(SMTPServer)
class SMTPServerAdmin(admin.ModelAdmin):
    list_display = ("alias", "host", "port", "username", "from_email", "use_tls", "use_ssl")
    list_display_links = ("alias",)
    fieldsets = (
        (None, {"fields": ("alias",)}),
        (
            _("Connection"),
            {"fields": ("host", "port", "username", "password", "use_tls", "use_ssl", "timeout")},
        ),
        (_("Headers"), {"fields": ("from_email", "reply_to")}),
    )
    actions = ["test_connection"]

    @admin.action(description=_("Test SMTP connection"))
    def test_connection(self, request, queryset):
        for server in queryset:
            ok = server.check_connection()
            if ok:
                self.message_user(
                    request,
                    _("%(alias)s: connection OK") % {"alias": server.alias},
                    messages.SUCCESS,
                )
            else:
                self.message_user(
                    request,
                    _("%(alias)s: connection failed") % {"alias": server.alias},
                    messages.ERROR,
                )
