import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.segurados.models import Segurado

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
def segurado(db):
    return Segurado.objects.create(
        cnpj="12.345.678/0001-90",
        nome="Segurado Teste",
        natureza_juridica="Sociedade Limitada",
        cidade="Fortaleza",
        estado="CE",
    )


# ─── Autenticação ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSeguradoAutenticacao:
    """Endpoints sem token devem retornar 401 — nunca expor dados."""

    def test_listar_sem_token_retorna_401(self, client):
        resp = client.get(reverse("segurado-list-create"))
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_criar_sem_token_retorna_401(self, client):
        resp = client.post(reverse("segurado-list-create"), {"cnpj": "000", "nome": "X"}, format="json")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_detalhe_sem_token_retorna_401(self, client, segurado):
        resp = client.get(reverse("segurado-detail", args=[segurado.pk]))
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_editar_sem_token_retorna_401(self, client, segurado):
        resp = client.patch(reverse("segurado-detail", args=[segurado.pk]), {"nome": "Hacker"}, format="json")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_excluir_sem_token_retorna_401(self, client, segurado):
        resp = client.delete(reverse("segurado-detail", args=[segurado.pk]))
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# ─── Unicidade de CNPJ ────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSeguradoCnpjUnico:
    """CNPJ duplicado deve ser rejeitado — dois segurados com o mesmo
    documento causariam inconsistência nos dados."""

    def test_cnpj_duplicado_retorna_400(self, auth_client, segurado):
        resp = auth_client.post(
            reverse("segurado-list-create"),
            {"cnpj": segurado.cnpj, "nome": "Outro Segurado"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_cnpj_unico_permite_cadastro(self, auth_client, db):
        resp = auth_client.post(
            reverse("segurado-list-create"),
            {"cnpj": "98.765.432/0001-10", "nome": "Novo Segurado"},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED

    def test_atualizar_cnpj_para_existente_retorna_400(self, auth_client, segurado, db):
        outro = Segurado.objects.create(cnpj="00.000.000/0001-00", nome="Outro")
        resp = auth_client.patch(
            reverse("segurado-detail", args=[outro.pk]),
            {"cnpj": segurado.cnpj},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ─── Campos obrigatórios ──────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSeguradoCamposObrigatorios:
    """Campos críticos ausentes devem ser rejeitados na entrada."""

    def test_criar_sem_nome_retorna_400(self, auth_client, db):
        resp = auth_client.post(
            reverse("segurado-list-create"),
            {"cnpj": "11.111.111/0001-11"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_criar_sem_cnpj_retorna_400(self, auth_client, db):
        resp = auth_client.post(
            reverse("segurado-list-create"),
            {"nome": "Sem Documento"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ─── Observações ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSeguradoObservacoes:
    """Observações com mais de 500 caracteres devem ser rejeitadas."""

    def test_observacoes_acima_de_500_retorna_400(self, auth_client, db):
        resp = auth_client.post(
            reverse("segurado-list-create"),
            {"cnpj": "22.222.222/0001-22", "nome": "Segurado X", "observacoes": "x" * 501},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_observacoes_nulas_sao_aceitas(self, auth_client, db):
        resp = auth_client.post(
            reverse("segurado-list-create"),
            {"cnpj": "33.333.333/0001-33", "nome": "Segurado Y", "observacoes": None},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED


# ─── CRUD básico ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSeguradoCRUD:
    """Fluxo principal — se quebrar, a tela inteira para de funcionar."""

    def test_listar_retorna_lista(self, auth_client, segurado):
        resp = auth_client.get(reverse("segurado-list-create"))
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["data"]) == 1

    def test_busca_por_nome(self, auth_client, segurado, db):
        Segurado.objects.create(cnpj="99.999.999/0001-99", nome="Outro Totalmente Diferente")
        resp = auth_client.get(reverse("segurado-list-create"), {"search": "Segurado Teste"})
        assert resp.status_code == status.HTTP_200_OK
        assert all("Segurado Teste" in s["nome"] for s in resp.data["data"])

    def test_detalhe_retorna_segurado(self, auth_client, segurado):
        resp = auth_client.get(reverse("segurado-detail", args=[segurado.pk]))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["data"]["cnpj"] == segurado.cnpj

    def test_detalhe_inexistente_retorna_404(self, auth_client, db):
        resp = auth_client.get(reverse("segurado-detail", args=[99999]))
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_patch_atualiza_campo(self, auth_client, segurado):
        resp = auth_client.patch(
            reverse("segurado-detail", args=[segurado.pk]),
            {"nome": "Nome Atualizado"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["data"]["nome"] == "Nome Atualizado"
        segurado.refresh_from_db()
        assert segurado.nome == "Nome Atualizado"

    def test_delete_remove_do_banco(self, auth_client, segurado):
        pk = segurado.pk
        resp = auth_client.delete(reverse("segurado-detail", args=[pk]))
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not Segurado.objects.filter(pk=pk).exists()
