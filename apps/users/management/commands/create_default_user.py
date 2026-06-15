from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'Creates a default superuser'

    def handle(self, *args, **options):
        User = get_user_model()
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'senha')
            self.stdout.write(self.style.SUCCESS('Successfully created default user "admin" with password "senha"'))
        else:
            self.stdout.write(self.style.WARNING('Default user "admin" already exists'))
