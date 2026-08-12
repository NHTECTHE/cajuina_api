from django.urls import path

from apps.apolices.api.v1.views import CotacaoEmitirView

from .views import (
    CotacaoDetailView,
    CotacaoEmailPreviewView,
    CotacaoEnviarEmailView,
    CotacaoListCreateView,
)

urlpatterns = [
    path("", CotacaoListCreateView.as_view(), name="cotacao-list-create"),
    path("<int:pk>/", CotacaoDetailView.as_view(), name="cotacao-detail"),
    path("<int:pk>/emitir/", CotacaoEmitirView.as_view(), name="cotacao-emitir"),
    path(
        "<int:pk>/email-preview/",
        CotacaoEmailPreviewView.as_view(),
        name="cotacao-email-preview",
    ),
    path(
        "<int:pk>/enviar-email/",
        CotacaoEnviarEmailView.as_view(),
        name="cotacao-enviar-email",
    ),
]
