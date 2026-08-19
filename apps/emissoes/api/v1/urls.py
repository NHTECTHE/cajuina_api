from django.urls import path

from .views import EmissaoCotarView, EmissaoEstadoView, EmissaoMinutaView

urlpatterns = [
    path("<int:pk>/emissao/", EmissaoEstadoView.as_view(), name="cotacao-emissao"),
    path(
        "<int:pk>/emissao/cotar/",
        EmissaoCotarView.as_view(),
        name="cotacao-emissao-cotar",
    ),
    path(
        "<int:pk>/emissao/minuta/",
        EmissaoMinutaView.as_view(),
        name="cotacao-emissao-minuta",
    ),
]
