from django.urls import path

from .views import (
    TomadorArquivoDetailView,
    TomadorArquivoListCreateView,
    TomadorAtividadeListView,
    TomadorDetailView,
    TomadorListCreateView,
    TomadorPremioAcumuladoView,
    TomadorSeguradoraDetailView,
    TomadorSeguradoraJuntoSolicitar,
    TomadorSeguradoraJuntoVerificar,
    TomadorSeguradoraListView,
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
    path(
        "<int:tomador_pk>/premio-acumulado/",
        TomadorPremioAcumuladoView.as_view(),
        name="tomador-premio-acumulado",
    ),
    path(
        "<int:tomador_pk>/atividades/",
        TomadorAtividadeListView.as_view(),
        name="tomador-atividades-list",
    ),
    path(
        "<int:tomador_pk>/seguradoras/<int:seguradora_pk>/junto/verificar/",
        TomadorSeguradoraJuntoVerificar.as_view(),
        name="tomador-seguradora-junto-verificar",
    ),
    path(
        "<int:tomador_pk>/seguradoras/<int:seguradora_pk>/junto/solicitar/",
        TomadorSeguradoraJuntoSolicitar.as_view(),
        name="tomador-seguradora-junto-solicitar",
    ),
]
