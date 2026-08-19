from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from apps.atividades.models import Atividade
from apps.seguradoras.models import Seguradora
from apps.tomadores.models import Tomador, TomadorSeguradora

# Fixtures localizados para tornar o arquivo de testes independente


@pytest.fixture
def client():
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def user(db):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return User.objects.create_user(email="tester@empresa.com", password="senha123")


@pytest.fixture
def auth_client(client, user):
    from django.urls import reverse

    resp = client.post(
        reverse("token_obtain_pair"),
        {"email": "tester@empresa.com", "password": "senha123"},
        format="json",
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")
    return client


@pytest.fixture
def tomador(db):
    return Tomador.objects.create(cnpj="12.345.678/0001-90", nome="Construtora Teste")


@pytest.fixture
def junto(db):
    return Seguradora.objects.create(nome="Junto Seguros", premio_minimo="140.00", vencimento_dias=20)


@pytest.mark.django_db
class TestJuntoIntegration:
    def test_verificar_found_sets_cadastro_ok(self, auth_client, tomador, junto, monkeypatch):
        # Mockar o client via monkeypatch na importação usada pelos serviços
        from shared.integracoes.junto import client as junto_client_module

        class FakeClient:
            def __init__(self, seguradora):
                self.seguradora = seguradora

            def consultar_tomador(self, cnpj):
                return {"cnpj": "12345678000190", "validade": (timezone.now().date() + timedelta(days=30)).isoformat()}

        monkeypatch.setattr(junto_client_module, "JuntoClient", FakeClient)

        url = reverse("tomador-seguradora-junto-verificar", args=[tomador.pk, junto.pk])
        resp = auth_client.post(url, {}, format="json")

        assert resp.status_code == status.HTTP_200_OK
        data = resp.data["data"]
        assert data["status"] == TomadorSeguradora.Status.CADASTRO_OK

        vinculo = TomadorSeguradora.objects.get(tomador=tomador, seguradora=junto)
        assert vinculo.status == TomadorSeguradora.Status.CADASTRO_OK
        assert vinculo.junto_data_ultima_verificacao is not None
        assert vinculo.junto_validade_cadastro is not None

    def test_verificar_not_found_keeps_sem_cadastro(self, auth_client, tomador, junto, monkeypatch):
        from shared.integracoes.junto import client as junto_client_module

        class FakeClient:
            def __init__(self, seguradora):
                self.seguradora = seguradora

            def consultar_tomador(self, cnpj):
                return None

        monkeypatch.setattr(junto_client_module, "JuntoClient", FakeClient)

        url = reverse("tomador-seguradora-junto-verificar", args=[tomador.pk, junto.pk])
        resp = auth_client.post(url, {}, format="json")

        assert resp.status_code == status.HTTP_200_OK
        data = resp.data["data"]
        assert data["status"] == TomadorSeguradora.Status.SEM_CADASTRO

        vinculo = TomadorSeguradora.objects.get(tomador=tomador, seguradora=junto)
        assert vinculo.status == TomadorSeguradora.Status.SEM_CADASTRO

    def test_solicitar_creates_activity_and_prevents_duplicate(self, auth_client, tomador, junto, monkeypatch):
        from shared.integracoes.junto import client as junto_client_module

        class FakeClient:
            def __init__(self, seguradora):
                self.seguradora = seguradora

            def solicitar_cadastro_tomador(self, dados):
                return {"status": "processing"}

            def consultar_tomador(self, cnpj):
                return None

        monkeypatch.setattr(junto_client_module, "JuntoClient", FakeClient)

        url = reverse("tomador-seguradora-junto-solicitar", args=[tomador.pk, junto.pk])
        resp1 = auth_client.post(url, {}, format="json")
        assert resp1.status_code == status.HTTP_200_OK

        vinculo = TomadorSeguradora.objects.get(tomador=tomador, seguradora=junto)

        # Deve existir uma atividade registrada
        atividades = Atividade.objects.filter(entidade="TomadorSeguradora", object_id=vinculo.id, acao="Criação")
        assert atividades.count() == 1

        # Segunda solicitação imediata não cria nova atividade
        resp2 = auth_client.post(url, {}, format="json")
        assert resp2.status_code == status.HTTP_200_OK
        atividades = Atividade.objects.filter(entidade="TomadorSeguradora", object_id=vinculo.id, acao="Criação")
        assert atividades.count() == 1
