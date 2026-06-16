from django.urls import path
from .views import TomadorListCreateView, TomadorDetailView

urlpatterns = [
    path("", TomadorListCreateView.as_view(), name="tomador-list-create"),
    path("<int:pk>/", TomadorDetailView.as_view(), name="tomador-detail"),
]
