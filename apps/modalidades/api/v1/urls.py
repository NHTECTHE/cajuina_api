from django.urls import path
from .views import ModalidadeListCreateView, ModalidadeDetailView

urlpatterns = [
    path('', ModalidadeListCreateView.as_view(), name='modalidade-list-create'),
    path('<int:pk>/', ModalidadeDetailView.as_view(), name='modalidade-detail'),
]
