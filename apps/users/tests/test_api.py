import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status

User = get_user_model()

@pytest.fixture
def api_client():
    from rest_framework.test import APIClient
    return APIClient()

@pytest.fixture
def create_user(db):
    def make_user(**kwargs):
        kwargs.setdefault('password', 'senha')
        if 'username' not in kwargs:
            kwargs['username'] = 'admin'
        return User.objects.create_user(**kwargs)
    return make_user

@pytest.mark.django_db
class TestAuthAPI:
    def test_obtain_token_pair(self, api_client, create_user):
        user = create_user(username='testuser', password='testpassword')
        url = reverse('token_obtain_pair')
        
        response = api_client.post(url, {
            'username': 'testuser',
            'password': 'testpassword'
        }, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data

    def test_obtain_token_pair_invalid_credentials(self, api_client, create_user):
        user = create_user(username='testuser', password='testpassword')
        url = reverse('token_obtain_pair')
        
        response = api_client.post(url, {
            'username': 'testuser',
            'password': 'wrongpassword'
        }, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert 'access' not in response.data

    def test_refresh_token(self, api_client, create_user):
        user = create_user(username='testuser', password='testpassword')
        url_obtain = reverse('token_obtain_pair')
        
        response_obtain = api_client.post(url_obtain, {
            'username': 'testuser',
            'password': 'testpassword'
        }, format='json')
        
        refresh_token = response_obtain.data['refresh']
        
        url_refresh = reverse('token_refresh')
        response_refresh = api_client.post(url_refresh, {
            'refresh': refresh_token
        }, format='json')
        
        assert response_refresh.status_code == status.HTTP_200_OK
        assert 'access' in response_refresh.data
