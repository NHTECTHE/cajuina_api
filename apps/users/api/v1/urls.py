from django.urls import path
from .views import (
    UserRegistrationView,
    UserActivationView,
    UserMeView,
    UserListCreateView,
    UserDetailView,
)

urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('activate/<str:uidb64>/<str:token>/', UserActivationView.as_view(), name='activate'),
    path('me/', UserMeView.as_view(), name='me'),
    path('', UserListCreateView.as_view(), name='usuario-list-create'),
    path('<int:pk>/', UserDetailView.as_view(), name='usuario-detail'),
]
