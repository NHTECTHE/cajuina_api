from django.urls import path
from .views import (
    MatrizView,
    ModalidadeDetailView,
    ModalidadeListCreateView,
    ModalidadeSeguradoraDetailView,
    ModalidadeSeguradoraListView,
)

urlpatterns = [
    path('', ModalidadeListCreateView.as_view(), name='modalidade-list-create'),
    # Antes de '<int:pk>/' para 'matriz' não ser lido como id.
    path('matriz/', MatrizView.as_view(), name='modalidade-matriz'),
    path('<int:pk>/', ModalidadeDetailView.as_view(), name='modalidade-detail'),
    path(
        '<int:modalidade_pk>/seguradoras/',
        ModalidadeSeguradoraListView.as_view(),
        name='modalidade-seguradora-list',
    ),
    path(
        '<int:modalidade_pk>/seguradoras/<int:seguradora_pk>/',
        ModalidadeSeguradoraDetailView.as_view(),
        name='modalidade-seguradora-detail',
    ),
]
