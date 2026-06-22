from django.urls import path
from .views import UserRegistrationView, UserActivationView, UserMeView

app_name = 'users_v1'

urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('activate/<str:uidb64>/<str:token>/', UserActivationView.as_view(), name='activate'),
    path('me/', UserMeView.as_view(), name='me'),
]
