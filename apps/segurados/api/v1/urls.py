from django.urls import path

from .views import SeguradoDetailView, SeguradoListCreateView

urlpatterns = [
    path("", SeguradoListCreateView.as_view(), name="segurado-list-create"),
    path("<int:pk>/", SeguradoDetailView.as_view(), name="segurado-detail"),
]
