from django.urls import path
from .views import ProdutorListCreateView, ProdutorDetailView

urlpatterns = [
    path("", ProdutorListCreateView.as_view(), name="produtor-list-create"),
    path("<int:pk>/", ProdutorDetailView.as_view(), name="produtor-detail"),
]
