import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from apps.atividades.models import Atividade

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
class TestLoginPorEmail:
    def test_login_com_email_retorna_tokens(self, api_client):
        User.objects.create_user(email="joao@empresa.com", password="senha123")

        resp = api_client.post(
            reverse("token_obtain_pair"),
            {"email": "joao@empresa.com", "password": "senha123"},
            format="json",
        )

        assert resp.status_code == 200
        assert "access" in resp.data
        assert "refresh" in resp.data

    def test_login_com_senha_errada_retorna_401(self, api_client):
        User.objects.create_user(email="joao@empresa.com", password="senha123")

        resp = api_client.post(
            reverse("token_obtain_pair"),
            {"email": "joao@empresa.com", "password": "errada"},
            format="json",
        )

        assert resp.status_code == 401

    def test_login_com_campo_username_retorna_400(self, api_client):
        """O campo username não existe mais — o payload antigo deve ser recusado."""
        User.objects.create_user(email="joao@empresa.com", password="senha123")

        resp = api_client.post(
            reverse("token_obtain_pair"),
            {"username": "joao@empresa.com", "password": "senha123"},
            format="json",
        )

        assert resp.status_code == 400
        assert "email" in resp.data

    def test_login_bem_sucedido_registra_atividade(self, api_client):
        User.objects.create_user(
            email="joao@empresa.com", password="senha123", first_name="João"
        )

        api_client.post(
            reverse("token_obtain_pair"),
            {"email": "joao@empresa.com", "password": "senha123"},
            format="json",
        )

        atividade = Atividade.objects.filter(acao="LOGIN").first()
        assert atividade is not None
        assert atividade.usuario_nome == "João"
