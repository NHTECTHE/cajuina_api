from django.urls import path

from .views import (
    ApoliceDetailView,
    ApoliceEmailPreviewView,
    ApoliceEnviarEmailView,
    ApoliceListView,
)

urlpatterns = [
    path("", ApoliceListView.as_view(), name="apolice-list"),
    path("<int:pk>/", ApoliceDetailView.as_view(), name="apolice-detail"),
    path(
        "<int:pk>/email-preview/",
        ApoliceEmailPreviewView.as_view(),
        name="apolice-email-preview",
    ),
    path(
        "<int:pk>/enviar-email/",
        ApoliceEnviarEmailView.as_view(),
        name="apolice-enviar-email",
    ),
]
