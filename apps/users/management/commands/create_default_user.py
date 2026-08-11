from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

EMAIL_PADRAO = "admin@example.com"


class Command(BaseCommand):
    help = "Creates a default superuser"

    def handle(self, *args, **options):
        User = get_user_model()
        if not User.objects.filter(email=EMAIL_PADRAO).exists():
            User.objects.create_superuser(email=EMAIL_PADRAO, password="senha")
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created default user "{EMAIL_PADRAO}" with password "senha"'
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'Default user "{EMAIL_PADRAO}" already exists')
            )
