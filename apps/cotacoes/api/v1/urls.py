from django.urls import path

from apps.apolices.api.v1.views import CotacaoEmitirView

from .views import CotacaoAprovarView, CotacaoDetailView, CotacaoListCreateView

urlpatterns = [
    path('', CotacaoListCreateView.as_view(), name='cotacao-list-create'),
    path('<int:pk>/', CotacaoDetailView.as_view(), name='cotacao-detail'),
    path('<int:pk>/aprovar/', CotacaoAprovarView.as_view(), name='cotacao-aprovar'),
    path('<int:pk>/emitir/', CotacaoEmitirView.as_view(), name='cotacao-emitir'),
]
