from django.urls import path
from .views import SeguradoraListCreateView, SeguradoraDetailView

urlpatterns = [
    path("", SeguradoraListCreateView.as_view(), name="seguradora-list-create"),
    path("<int:pk>/", SeguradoraDetailView.as_view(), name="seguradora-detail"),
]
