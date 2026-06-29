from django.urls import path
from .views import (
    UserRegistrationView,
    UserActivationView,
    UserMeView,
    UserListCreateView,
    UserDetailView,
    PasswordResetView,
    PasswordResetConfirmView,
)

urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('activate/<str:uidb64>/<str:token>/', UserActivationView.as_view(), name='activate'),
    path('me/', UserMeView.as_view(), name='me'),
    path('password-reset/', PasswordResetView.as_view(), name='password_reset'),
    path('password-reset-confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('', UserListCreateView.as_view(), name='usuario-list-create'),
    path('<int:pk>/', UserDetailView.as_view(), name='usuario-detail'),
]
