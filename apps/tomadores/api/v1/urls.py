from django.urls import path
from .views import (
    TomadorListCreateView,
    TomadorDetailView,
    TomadorArquivoListCreateView,
    TomadorArquivoDetailView,
    TomadorSeguradoraListView,
    TomadorSeguradoraDetailView,
)

urlpatterns = [
    path("", TomadorListCreateView.as_view(), name="tomador-list-create"),
    path("<int:pk>/", TomadorDetailView.as_view(), name="tomador-detail"),
    path(
        "<int:tomador_pk>/arquivos/",
        TomadorArquivoListCreateView.as_view(),
        name="tomador-arquivo-list-create",
    ),
    path(
        "<int:tomador_pk>/arquivos/<int:pk>/",
        TomadorArquivoDetailView.as_view(),
        name="tomador-arquivo-detail",
    ),
    path(
        "<int:tomador_pk>/seguradoras/",
        TomadorSeguradoraListView.as_view(),
        name="tomador-seguradora-list",
    ),
    path(
        "<int:tomador_pk>/seguradoras/<int:seguradora_pk>/",
        TomadorSeguradoraDetailView.as_view(),
        name="tomador-seguradora-detail",
    ),
]
