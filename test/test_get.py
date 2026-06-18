import os
import django
import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from apps.tomadores.models import Tomador
from apps.tomadores.api.v1.serializers import TomadorSerializer

queryset = Tomador.objects.all()
serializer = TomadorSerializer(queryset, many=True)
print("Type of serializer.data:", type(serializer.data))

# Let's also check if DRF pagination is active by default.
from rest_framework.settings import api_settings
print("Pagination class:", api_settings.DEFAULT_PAGINATION_CLASS)
