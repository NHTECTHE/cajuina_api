from django.urls import path

from .views import NotificacaoListView, NotificacaoMarcarLidasView

urlpatterns = [
    path("", NotificacaoListView.as_view(), name="notificacoes-list"),
    path(
        "lidas/", NotificacaoMarcarLidasView.as_view(), name="notificacoes-marcar-lidas"
    ),
]
