from django.urls import path
from .views import AtividadeListView

urlpatterns = [
    path('', AtividadeListView.as_view(), name='atividade_list'),
]
