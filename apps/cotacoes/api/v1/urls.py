from django.urls import path

from .views import CotacaoAprovarView, CotacaoDetailView, CotacaoListCreateView

urlpatterns = [
    path('', CotacaoListCreateView.as_view(), name='cotacao-list-create'),
    path('<int:pk>/', CotacaoDetailView.as_view(), name='cotacao-detail'),
    path('<int:pk>/aprovar/', CotacaoAprovarView.as_view(), name='cotacao-aprovar'),
]
