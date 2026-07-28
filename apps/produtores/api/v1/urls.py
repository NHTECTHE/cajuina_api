from django.urls import path

from .views import ProdutorDetailView, ProdutorListCreateView

urlpatterns = [
    path("", ProdutorListCreateView.as_view(), name="produtor-list-create"),
    path("<int:pk>/", ProdutorDetailView.as_view(), name="produtor-detail"),
]
