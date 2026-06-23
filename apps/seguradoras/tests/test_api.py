import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.seguradoras.models import Seguradora

User = get_user_model()

# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="tester", password="senha123")


@pytest.fixture
def auth_client(client, user):
    resp = client.post(reverse("token_obtain_pair"), {"username": "tester", "password": "senha123"}, format="json")
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")
    return client


@pytest.fixture
def seguradora(db):
    return Seguradora.objects.create(
        nome="Seguradora Teste",
        valor_licitacao="1000000.00",
        valor_execucao="500000.00",
        taxa_comissao="5.00",
        dia_vencimento=15,
    )


# ─── Autenticação ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSeguradoraAutenticacao:
    """Endpoints sem token devem retornar 401."""

    def test_listar_sem_token_retorna_401(self, client):
        resp = client.get(reverse("seguradora-list-create"))
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_criar_sem_token_retorna_401(self, client):
        resp = client.post(reverse("seguradora-list-create"), {"nome": "X"}, format="json")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_detalhe_sem_token_retorna_401(self, client, seguradora):
        resp = client.get(reverse("seguradora-detail", args=[seguradora.pk]))
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_editar_sem_token_retorna_401(self, client, seguradora):
        resp = client.patch(reverse("seguradora-detail", args=[seguradora.pk]), {"nome": "X"}, format="json")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_excluir_sem_token_retorna_401(self, client, seguradora):
        resp = client.delete(reverse("seguradora-detail", args=[seguradora.pk]))
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# ─── Campos obrigatórios ──────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSeguradoraCamposObrigatorios:
    def test_criar_sem_nome_retorna_400(self, auth_client, db):
        resp = auth_client.post(reverse("seguradora-list-create"), {}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ─── Validações financeiras ───────────────────────────────────────────────────

@pytest.mark.django_db
class TestSeguradoraValidacoes:
    """Valores fora de range devem ser rejeitados."""

    def test_taxa_comissao_acima_de_100_retorna_400(self, auth_client, db):
        resp = auth_client.post(
            reverse("seguradora-list-create"),
            {"nome": "Seg X", "taxa_comissao": "101.00"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_taxa_comissao_negativa_retorna_400(self, auth_client, db):
        resp = auth_client.post(
            reverse("seguradora-list-create"),
            {"nome": "Seg X", "taxa_comissao": "-1.00"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_dia_vencimento_zero_retorna_400(self, auth_client, db):
        resp = auth_client.post(
            reverse("seguradora-list-create"),
            {"nome": "Seg X", "dia_vencimento": 0},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_dia_vencimento_32_retorna_400(self, auth_client, db):
        resp = auth_client.post(
            reverse("seguradora-list-create"),
            {"nome": "Seg X", "dia_vencimento": 32},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_valor_licitacao_negativo_retorna_400(self, auth_client, db):
        resp = auth_client.post(
            reverse("seguradora-list-create"),
            {"nome": "Seg X", "valor_licitacao": "-100.00"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_valor_execucao_negativo_retorna_400(self, auth_client, db):
        resp = auth_client.post(
            reverse("seguradora-list-create"),
            {"nome": "Seg X", "valor_execucao": "-100.00"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_campos_opcionais_nulos_sao_aceitos(self, auth_client, db):
        resp = auth_client.post(
            reverse("seguradora-list-create"),
            {"nome": "Seg Mínima"},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.data["data"]
        assert data["valor_licitacao"] is None
        assert data["valor_execucao"] is None
        assert data["taxa_comissao"] is None
        assert data["dia_vencimento"] is None


# ─── CRUD básico ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSeguradoraCRUD:
    """Fluxo principal da tela de seguradoras."""

    def test_listar_retorna_lista(self, auth_client, seguradora):
        resp = auth_client.get(reverse("seguradora-list-create"))
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["data"]) == 1

    def test_busca_por_nome(self, auth_client, seguradora, db):
        Seguradora.objects.create(nome="Outra Totalmente Diferente")
        resp = auth_client.get(reverse("seguradora-list-create"), {"search": "Seguradora Teste"})
        assert resp.status_code == status.HTTP_200_OK
        assert all("Seguradora Teste" in s["nome"] for s in resp.data["data"])

    def test_filtro_ativo(self, auth_client, seguradora, db):
        Seguradora.objects.create(nome="Inativa", ativo=False)
        resp = auth_client.get(reverse("seguradora-list-create"), {"ativo": "true"})
        assert resp.status_code == status.HTTP_200_OK
        assert all(s["ativo"] for s in resp.data["data"])

    def test_detalhe_retorna_seguradora(self, auth_client, seguradora):
        resp = auth_client.get(reverse("seguradora-detail", args=[seguradora.pk]))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["data"]["nome"] == seguradora.nome

    def test_detalhe_inexistente_retorna_404(self, auth_client, db):
        resp = auth_client.get(reverse("seguradora-detail", args=[99999]))
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_patch_atualiza_campo(self, auth_client, seguradora):
        resp = auth_client.patch(
            reverse("seguradora-detail", args=[seguradora.pk]),
            {"nome": "Nome Atualizado"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["data"]["nome"] == "Nome Atualizado"
        seguradora.refresh_from_db()
        assert seguradora.nome == "Nome Atualizado"

    def test_delete_remove_do_banco(self, auth_client, seguradora):
        pk = seguradora.pk
        resp = auth_client.delete(reverse("seguradora-detail", args=[pk]))
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not Seguradora.objects.filter(pk=pk).exists()

    def test_criar_com_todos_os_campos(self, auth_client, db):
        resp = auth_client.post(
            reverse("seguradora-list-create"),
            {
                "nome": "Nova Seguradora",
                "valor_licitacao": "2000000.00",
                "valor_execucao": "1500000.00",
                "taxa_comissao": "3.50",
                "dia_vencimento": 10,
                "ativo": True,
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.data["data"]
        assert data["nome"] == "Nova Seguradora"
        assert data["taxa_comissao"] == "3.50"
        assert data["dia_vencimento"] == 10
