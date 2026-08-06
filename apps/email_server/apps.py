from django.apps import AppConfig


class EmailServerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.email_server"
    label = "email_server"
    verbose_name = "Email server"
