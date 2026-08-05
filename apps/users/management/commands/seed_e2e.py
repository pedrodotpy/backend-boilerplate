from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

User = get_user_model()

E2E_PASSWORD = "e2epass123"

E2E_ADMIN_EMAIL = "e2e-admin@example.com"
E2E_VIEWER_EMAIL = "e2e-viewer@example.com"


class Command(BaseCommand):
    help = "Seed deterministic users for Playwright E2E tests."

    def add_arguments(self, parser):
        parser.add_argument(
            "--extra-users",
            type=int,
            default=0,
            help="Create N extra users (e2e-extra-0@example.com …) for pagination tests.",
        )

    def handle(self, *args, **options):
        admin, created = User.objects.get_or_create(
            email=E2E_ADMIN_EMAIL,
            defaults={"is_staff": True, "is_superuser": True},
        )
        admin.is_staff = True
        admin.is_superuser = True
        admin.is_active = True
        admin.set_password(E2E_PASSWORD)
        admin.save()
        self.stdout.write(
            self.style.SUCCESS(
                f"{'Created' if created else 'Updated'} superuser {E2E_ADMIN_EMAIL}"
            )
        )

        viewer, created = User.objects.get_or_create(
            email=E2E_VIEWER_EMAIL,
            defaults={"is_staff": False, "is_superuser": False},
        )
        viewer.is_staff = False
        viewer.is_superuser = False
        viewer.is_active = True
        viewer.set_password(E2E_PASSWORD)
        viewer.save()
        viewer.user_permissions.clear()
        content_type = ContentType.objects.get_for_model(User)
        view_perm = Permission.objects.get(
            content_type=content_type,
            codename="view_user",
        )
        viewer.user_permissions.add(view_perm)
        self.stdout.write(
            self.style.SUCCESS(
                f"{'Created' if created else 'Updated'} viewer {E2E_VIEWER_EMAIL}"
            )
        )

        extra = options["extra_users"]
        for i in range(extra):
            email = f"e2e-extra-{i}@example.com"
            user, created = User.objects.get_or_create(
                email=email,
                defaults={"is_active": True},
            )
            if created:
                user.set_password(E2E_PASSWORD)
                user.save()
        if extra:
            self.stdout.write(
                self.style.SUCCESS(f"Ensured {extra} extra users for pagination")
            )
