from django.urls import path
from .views import RegisterView, ActivateView, UserMeView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('activate/', ActivateView.as_view(), name='activate'),
    path('me/', UserMeView.as_view(), name='me'),
]

