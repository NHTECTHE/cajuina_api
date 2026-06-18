import os
import django
import requests

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from apps.users.models import CustomUser

user, _ = CustomUser.objects.get_or_create(username='admin_test', defaults={'is_superuser': True, 'is_staff': True})
if _:
    user.set_password('admin')
    user.save()

# Login to get JWT token
res = requests.post('http://localhost:8000/api/v1/auth/login/', json={'username': 'admin_test', 'password': 'admin'})
token = res.json().get('access')

# Now curl Next.js endpoint. We mock the cookie by sending the token as cookie or auth header.
res_api = requests.get('http://localhost:8000/api/v1/tomadores/', headers={'Authorization': f'Bearer {token}'})
print("Backend GET tomadores status:", res_api.status_code)
print("Backend GET tomadores JSON:", res_api.json())
print("Next.js GET tomadores JSON:", next_res.json())
