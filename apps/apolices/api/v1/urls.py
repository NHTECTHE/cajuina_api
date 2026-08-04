from django.urls import path

from .views import ApoliceDetailView, ApoliceListView

urlpatterns = [
    path("", ApoliceListView.as_view(), name="apolice-list"),
    path("<int:pk>/", ApoliceDetailView.as_view(), name="apolice-detail"),
]
