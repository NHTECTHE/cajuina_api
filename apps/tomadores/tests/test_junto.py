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

    def test_consultar_taxa_read_only_and_records_activity(self, auth_client, tomador, junto, monkeypatch):
        from decimal import Decimal

        from shared.integracoes.junto import client as junto_client_module

        class FakeClient:
            def __init__(self, seguradora):
                self.seguradora = seguradora

            def consultar_limites_e_taxas(self, cnpj):
                return {
                    "limite_disponivel": "500000.00",
                    "modalidade_id": "99",
                    "modalidade_descricao": "Licitante",
                    "taxa": Decimal("1.2478"),
                    "data_consulta": "2026-08-19T18:00:00Z",
                    "origem": "junto",
                }

        monkeypatch.setattr(junto_client_module, "JuntoClient", FakeClient)

        url = reverse("tomador-seguradora-junto-taxa", args=[tomador.pk, junto.pk])
        resp = auth_client.post(url, {}, format="json")

        assert resp.status_code == status.HTTP_200_OK
        data = resp.data["data"]
        assert data["taxa"] == Decimal("1.2478")
        assert data["modalidade_id"] == "99"
        assert data["modalidade_descricao"] == "Licitante"

        # Verifica que o endpoint NÃO alterou o banco de dados diretamente
        vinculo = TomadorSeguradora.objects.get(tomador=tomador, seguradora=junto)
        assert vinculo.taxa == Decimal("0")

        # Verifica que a consulta foi registrada no histórico de atividades
        atividades = Atividade.objects.filter(entidade="TomadorSeguradora", object_id=vinculo.id, acao="Consulta")
        assert atividades.count() == 1
        assert "Taxa consultada na Junto: 1.2478" in atividades.first().detalhes

    def test_taxa_6_casas_e_origem_salvas(self, auth_client, tomador, junto):
        from decimal import Decimal

        url = reverse("tomador-seguradora-list", args=[tomador.pk])
        payload = {
            "itens": [
                {
                    "seguradora": junto.pk,
                    "status": "sem_cadastro",
                    "taxa": "1.247800",
                    "taxa_origem": "junto",
                    "taxa_junto_modalidade_id": "99",
                    "taxa_junto_modalidade_descricao": "Licitante",
                    "taxa_data_atualizacao": "2026-08-19T18:00:00Z",
                    "premio_minimo": None,
                    "dias_vencimento": None,
                }
            ]
        }
        resp = auth_client.put(url, payload, format="json")
        assert resp.status_code == status.HTTP_200_OK

        vinculo = TomadorSeguradora.objects.get(tomador=tomador, seguradora=junto)
        assert vinculo.taxa == Decimal("1.2478")
        assert vinculo.taxa_origem == "junto"
        assert vinculo.taxa_junto_modalidade_id == "99"

    def test_edicao_manual_limpa_origem(self, auth_client, tomador, junto):
        from decimal import Decimal

        url = reverse("tomador-seguradora-list", args=[tomador.pk])
        payload = {
            "itens": [
                {
                    "seguradora": junto.pk,
                    "status": "sem_cadastro",
                    "taxa": "1.50",
                    "taxa_origem": "",
                    "taxa_junto_modalidade_id": "",
                    "taxa_junto_modalidade_descricao": "",
                    "taxa_data_atualizacao": None,
                    "premio_minimo": None,
                    "dias_vencimento": None,
                }
            ]
        }
        resp = auth_client.put(url, payload, format="json")
        assert resp.status_code == status.HTTP_200_OK

        vinculo = TomadorSeguradora.objects.get(tomador=tomador, seguradora=junto)
        assert vinculo.taxa == Decimal("1.5")
        assert vinculo.taxa_origem == ""
        assert vinculo.taxa_junto_modalidade_id == ""

    def test_taxa_com_mais_de_6_casas_retorna_erro(self, auth_client, tomador, junto):
        url = reverse("tomador-seguradora-list", args=[tomador.pk])
        payload = {
            "itens": [
                {
                    "seguradora": junto.pk,
                    "status": "sem_cadastro",
                    "taxa": "1.1234567",
                    "premio_minimo": None,
                    "dias_vencimento": None,
                }
            ]
        }
        resp = auth_client.put(url, payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_taxa_maior_ou_igual_1000_retorna_erro(self, auth_client, tomador, junto):
        url = reverse("tomador-seguradora-list", args=[tomador.pk])
        payload = {
            "itens": [
                {
                    "seguradora": junto.pk,
                    "status": "sem_cadastro",
                    "taxa": "1000.00",
                    "premio_minimo": None,
                    "dias_vencimento": None,
                }
            ]
        }
        resp = auth_client.put(url, payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

