import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.corretores.models import Corretor

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
def corretor(db):
    return Corretor.objects.create(
        cpf_cnpj="12.345.678/0001-90",
        nome="Corretor Teste",
        recebimento="pix",
        percentual="5.00",
        banco="Bradesco",
        agencia="1234",
        conta="56789-0",
        email="corretor@teste.com",
        telefone="(85) 99999-0000",
        url_saida="https://teste.com/saida",
    )


# ─── Autenticação ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestCorretorAutenticacao:
    """Endpoints sem token devem retornar 401 — nunca expor dados."""

    def test_listar_sem_token_retorna_401(self, client):
        resp = client.get(reverse("corretor-list-create"))
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_criar_sem_token_retorna_401(self, client):
        resp = client.post(reverse("corretor-list-create"), {"cpf_cnpj": "000", "nome": "X"}, format="json")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_detalhe_sem_token_retorna_401(self, client, corretor):
        resp = client.get(reverse("corretor-detail", args=[corretor.pk]))
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_editar_sem_token_retorna_401(self, client, corretor):
        resp = client.patch(reverse("corretor-detail", args=[corretor.pk]), {"nome": "Hacker"}, format="json")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_excluir_sem_token_retorna_401(self, client, corretor):
        resp = client.delete(reverse("corretor-detail", args=[corretor.pk]))
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# ─── Unicidade de CPF/CNPJ ────────────────────────────────────────────────────

@pytest.mark.django_db
class TestCorretorUnicidade:
    """CPF/CNPJ duplicado deve ser rejeitado — dois corretores com o mesmo
    documento causariam inconsistência em comissões e relatórios."""

    def test_cpf_cnpj_duplicado_retorna_400(self, auth_client, corretor):
        resp = auth_client.post(
            reverse("corretor-list-create"),
            {"cpf_cnpj": corretor.cpf_cnpj, "nome": "Outro Corretor"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_cpf_cnpj_unico_permite_cadastro(self, auth_client, db):
        resp = auth_client.post(
            reverse("corretor-list-create"),
            {"cpf_cnpj": "98.765.432/0001-10", "nome": "Novo Corretor"},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED

    def test_atualizar_cpf_cnpj_para_existente_retorna_400(self, auth_client, corretor, db):
        outro = Corretor.objects.create(cpf_cnpj="00.000.000/0001-00", nome="Outro")
        resp = auth_client.patch(
            reverse("corretor-detail", args=[outro.pk]),
            {"cpf_cnpj": corretor.cpf_cnpj},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ─── Campos obrigatórios ──────────────────────────────────────────────────────

@pytest.mark.django_db
class TestCorretorCamposObrigatorios:
    """Campos críticos ausentes devem ser rejeitados na entrada."""

    def test_criar_sem_nome_retorna_400(self, auth_client, db):
        resp = auth_client.post(
            reverse("corretor-list-create"),
            {"cpf_cnpj": "11.111.111/0001-11"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_criar_sem_cpf_cnpj_retorna_400(self, auth_client, db):
        resp = auth_client.post(
            reverse("corretor-list-create"),
            {"nome": "Sem Documento"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ─── Integridade dos dados financeiros ───────────────────────────────────────

@pytest.mark.django_db
class TestCorretorPercentual:
    """Percentual fora de 0–100 corromperia cálculos de comissão."""

    def test_percentual_acima_de_100_retorna_400(self, auth_client, db):
        resp = auth_client.post(
            reverse("corretor-list-create"),
            {"cpf_cnpj": "22.222.222/0001-22", "nome": "Corretor X", "percentual": "150.00"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_percentual_negativo_retorna_400(self, auth_client, db):
        resp = auth_client.post(
            reverse("corretor-list-create"),
            {"cpf_cnpj": "33.333.333/0001-33", "nome": "Corretor Y", "percentual": "-1.00"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_percentual_nulo_e_aceito(self, auth_client, db):
        resp = auth_client.post(
            reverse("corretor-list-create"),
            {"cpf_cnpj": "44.444.444/0001-44", "nome": "Corretor Z", "percentual": None},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["data"]["percentual"] is None

    def test_percentual_zero_e_aceito(self, auth_client, db):
        resp = auth_client.post(
            reverse("corretor-list-create"),
            {"cpf_cnpj": "55.555.555/0001-55", "nome": "Corretor W", "percentual": "0.00"},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED


# ─── CRUD básico ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestCorretorCRUD:
    """Fluxo principal — se quebrar, a tela inteira para de funcionar."""

    def test_listar_retorna_lista(self, auth_client, corretor):
        resp = auth_client.get(reverse("corretor-list-create"))
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["data"]) == 1

    def test_busca_por_nome(self, auth_client, corretor, db):
        Corretor.objects.create(cpf_cnpj="99.999.999/0001-99", nome="Outro Totalmente Diferente")
        resp = auth_client.get(reverse("corretor-list-create"), {"search": "Corretor Teste"})
        assert resp.status_code == status.HTTP_200_OK
        assert all("Corretor Teste" in c["nome"] for c in resp.data["data"])

    def test_detalhe_retorna_corretor(self, auth_client, corretor):
        resp = auth_client.get(reverse("corretor-detail", args=[corretor.pk]))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["data"]["cpf_cnpj"] == corretor.cpf_cnpj

    def test_detalhe_inexistente_retorna_404(self, auth_client, db):
        resp = auth_client.get(reverse("corretor-detail", args=[99999]))
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_patch_atualiza_campo(self, auth_client, corretor):
        resp = auth_client.patch(
            reverse("corretor-detail", args=[corretor.pk]),
            {"nome": "Nome Atualizado"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["data"]["nome"] == "Nome Atualizado"
        corretor.refresh_from_db()
        assert corretor.nome == "Nome Atualizado"

    def test_delete_remove_do_banco(self, auth_client, corretor):
        pk = corretor.pk
        resp = auth_client.delete(reverse("corretor-detail", args=[pk]))
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not Corretor.objects.filter(pk=pk).exists()
