from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.tomador.api.v1.views import TomadorViewSet

router = DefaultRouter()
router.register(r'', TomadorViewSet, basename='tomador')

urlpatterns = [
    path('', include(router.urls)),
]
