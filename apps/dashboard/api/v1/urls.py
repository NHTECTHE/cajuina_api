from django.urls import path

from .views import (
    DashboardComissoesView,
    DashboardNovosCadastrosView,
    DashboardPremioSeguradorasView,
    DashboardResumoView,
)

urlpatterns = [
    path("resumo/", DashboardResumoView.as_view(), name="dashboard-resumo"),
    path("comissoes/", DashboardComissoesView.as_view(), name="dashboard-comissoes"),
    path(
        "premio-seguradoras/",
        DashboardPremioSeguradorasView.as_view(),
        name="dashboard-premio-seguradoras",
    ),
    path(
        "novos-cadastros/",
        DashboardNovosCadastrosView.as_view(),
        name="dashboard-novos-cadastros",
    ),
]
