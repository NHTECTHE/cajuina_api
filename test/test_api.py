import os
import django
from django.test import Client
from apps.users.models import CustomUser

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

# Create a test user and login
user, _ = CustomUser.objects.get_or_create(username='admin', defaults={'is_superuser': True, 'is_staff': True})
if _: user.set_password('admin'); user.save()

client = Client()
client.force_login(user)

response = client.get('/api/v1/tomadores/')
print("Status Code:", response.status_code)
print("Response JSON:", response.json())
