from django.urls import path
from .views import CorretorListCreateView, CorretorDetailView

urlpatterns = [
    path("", CorretorListCreateView.as_view(), name="corretor-list-create"),
    path("<int:pk>/", CorretorDetailView.as_view(), name="corretor-detail"),
]
