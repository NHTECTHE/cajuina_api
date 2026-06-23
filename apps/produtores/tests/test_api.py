import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.corretores.models import Corretor
from apps.produtores.models import Produtor

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
    return Corretor.objects.create(cpf_cnpj="12.345.678/0001-90", nome="Corretora ABC")


@pytest.fixture
def produtor(db):
    return Produtor.objects.create(
        nome="Produtor Teste",
        email="produtor@teste.com",
        telefone="(85) 99999-0000",
        recebimento="comissao",
        percentual="5.00",
        meta="50000.00",
    )


@pytest.fixture
def produtor_com_corretora(db, corretor):
    return Produtor.objects.create(
        nome="Produtor Com Corretora",
        corretora=corretor,
        email="prod@corretora.com",
        recebimento="lucro",
        percentual="3.00",
    )


# ─── Autenticação ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProdutorAutenticacao:
    """Endpoints sem token devem retornar 401 — nunca expor dados."""

    def test_listar_sem_token_retorna_401(self, client):
        resp = client.get(reverse("produtor-list-create"))
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_criar_sem_token_retorna_401(self, client):
        resp = client.post(reverse("produtor-list-create"), {"nome": "X"}, format="json")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_detalhe_sem_token_retorna_401(self, client, produtor):
        resp = client.get(reverse("produtor-detail", args=[produtor.pk]))
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_editar_sem_token_retorna_401(self, client, produtor):
        resp = client.patch(reverse("produtor-detail", args=[produtor.pk]), {"nome": "Hacker"}, format="json")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_excluir_sem_token_retorna_401(self, client, produtor):
        resp = client.delete(reverse("produtor-detail", args=[produtor.pk]))
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# ─── Campos obrigatórios ──────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProdutorCamposObrigatorios:
    """Nome é o único campo obrigatório — demais são opcionais."""

    def test_criar_sem_nome_retorna_400(self, auth_client, db):
        resp = auth_client.post(
            reverse("produtor-list-create"),
            {"email": "x@y.com"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_criar_so_com_nome_retorna_201(self, auth_client, db):
        resp = auth_client.post(
            reverse("produtor-list-create"),
            {"nome": "Produtor Minimo"},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["data"]["nome"] == "Produtor Minimo"
        assert resp.data["data"]["corretora_id"] is None
        assert resp.data["data"]["corretora_nome"] is None
        assert resp.data["data"]["percentual"] is None
        assert resp.data["data"]["meta"] is None


# ─── Corretora FK ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProdutorCorretora:
    """Corretora é FK — deve aceitar id válido, rejeitar id inexistente."""

    def test_criar_com_corretora_valida(self, auth_client, corretor):
        resp = auth_client.post(
            reverse("produtor-list-create"),
            {"nome": "Produtor XYZ", "corretora_id": corretor.pk},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["data"]["corretora_id"] == corretor.pk
        assert resp.data["data"]["corretora_nome"] == corretor.nome

    def test_criar_sem_corretora_retorna_null(self, auth_client, db):
        resp = auth_client.post(
            reverse("produtor-list-create"),
            {"nome": "Sem Corretora"},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["data"]["corretora_id"] is None
        assert resp.data["data"]["corretora_nome"] is None

    def test_criar_com_corretora_inexistente_retorna_400(self, auth_client, db):
        resp = auth_client.post(
            reverse("produtor-list-create"),
            {"nome": "Produtor", "corretora_id": 99999},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_patch_atualiza_corretora(self, auth_client, produtor, corretor):
        resp = auth_client.patch(
            reverse("produtor-detail", args=[produtor.pk]),
            {"corretora_id": corretor.pk},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["data"]["corretora_id"] == corretor.pk
        assert resp.data["data"]["corretora_nome"] == corretor.nome

    def test_patch_remove_corretora_com_null(self, auth_client, produtor_com_corretora):
        resp = auth_client.patch(
            reverse("produtor-detail", args=[produtor_com_corretora.pk]),
            {"corretora_id": None},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["data"]["corretora_id"] is None
        assert resp.data["data"]["corretora_nome"] is None

    def test_excluir_corretora_nao_exclui_produtor(self, auth_client, produtor_com_corretora, corretor):
        corretor.delete()
        produtor_com_corretora.refresh_from_db()
        assert produtor_com_corretora.corretora is None
        resp = auth_client.get(reverse("produtor-detail", args=[produtor_com_corretora.pk]))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["data"]["corretora_id"] is None


# ─── Validação de percentual ──────────────────────────────────────────────────

@pytest.mark.django_db
class TestProdutorPercentual:
    """Percentual fora de 0–100 corromperia cálculos de comissão."""

    def test_percentual_acima_de_100_retorna_400(self, auth_client, db):
        resp = auth_client.post(
            reverse("produtor-list-create"),
            {"nome": "Produtor X", "percentual": "150.00"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_percentual_negativo_retorna_400(self, auth_client, db):
        resp = auth_client.post(
            reverse("produtor-list-create"),
            {"nome": "Produtor Y", "percentual": "-1.00"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_percentual_nulo_e_aceito(self, auth_client, db):
        resp = auth_client.post(
            reverse("produtor-list-create"),
            {"nome": "Produtor Z", "percentual": None},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["data"]["percentual"] is None

    def test_percentual_zero_e_aceito(self, auth_client, db):
        resp = auth_client.post(
            reverse("produtor-list-create"),
            {"nome": "Produtor W", "percentual": "0.00"},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED

    def test_percentual_cem_e_aceito(self, auth_client, db):
        resp = auth_client.post(
            reverse("produtor-list-create"),
            {"nome": "Produtor V", "percentual": "100.00"},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED


# ─── CRUD básico ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProdutorCRUD:
    """Fluxo principal — se quebrar, a tela inteira para de funcionar."""

    def test_listar_retorna_lista(self, auth_client, produtor):
        resp = auth_client.get(reverse("produtor-list-create"))
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["data"]) == 1

    def test_listar_retorna_envelope_data(self, auth_client, db):
        resp = auth_client.get(reverse("produtor-list-create"))
        assert resp.status_code == status.HTTP_200_OK
        assert "data" in resp.data
        assert isinstance(resp.data["data"], list)

    def test_criar_retorna_201_com_dados(self, auth_client, db):
        payload = {
            "nome": "Novo Produtor",
            "email": "novo@xyz.com",
            "telefone": "(11) 91234-5678",
            "recebimento": "lucro",
            "percentual": "3.50",
            "meta": "80000.00",
        }
        resp = auth_client.post(reverse("produtor-list-create"), payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.data["data"]
        assert data["nome"] == "Novo Produtor"
        assert data["recebimento"] == "lucro"
        assert data["percentual"] == "3.50"
        assert data["meta"] == "80000.00"
        assert data["ativo"] is True
        assert "id" in data
        assert "criado_em" in data

    def test_detalhe_retorna_produtor(self, auth_client, produtor):
        resp = auth_client.get(reverse("produtor-detail", args=[produtor.pk]))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["data"]["nome"] == produtor.nome

    def test_detalhe_inexistente_retorna_404(self, auth_client, db):
        resp = auth_client.get(reverse("produtor-detail", args=[99999]))
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_patch_atualiza_campo(self, auth_client, produtor):
        resp = auth_client.patch(
            reverse("produtor-detail", args=[produtor.pk]),
            {"nome": "Nome Atualizado"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["data"]["nome"] == "Nome Atualizado"
        produtor.refresh_from_db()
        assert produtor.nome == "Nome Atualizado"

    def test_patch_parcial_nao_altera_outros_campos(self, auth_client, produtor):
        resp = auth_client.patch(
            reverse("produtor-detail", args=[produtor.pk]),
            {"meta": "99000.00"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["data"]["email"] == produtor.email

    def test_delete_remove_do_banco(self, auth_client, produtor):
        pk = produtor.pk
        resp = auth_client.delete(reverse("produtor-detail", args=[pk]))
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not Produtor.objects.filter(pk=pk).exists()

    def test_delete_inexistente_retorna_404(self, auth_client, db):
        resp = auth_client.delete(reverse("produtor-detail", args=[99999]))
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ─── Busca ────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProdutorBusca:
    """Search deve filtrar por nome e nome da corretora (FK)."""

    def test_busca_por_nome(self, auth_client, produtor, db):
        Produtor.objects.create(nome="Totalmente Diferente")
        resp = auth_client.get(reverse("produtor-list-create"), {"search": "Produtor Teste"})
        assert resp.status_code == status.HTTP_200_OK
        nomes = [p["nome"] for p in resp.data["data"]]
        assert all("Produtor Teste" in n for n in nomes)

    def test_busca_por_nome_corretora(self, auth_client, produtor_com_corretora, db):
        Produtor.objects.create(nome="Outro sem corretora")
        resp = auth_client.get(reverse("produtor-list-create"), {"search": "Corretora ABC"})
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["data"]) == 1
        assert resp.data["data"][0]["corretora_nome"] == "Corretora ABC"

    def test_busca_sem_resultado_retorna_lista_vazia(self, auth_client, produtor):
        resp = auth_client.get(reverse("produtor-list-create"), {"search": "xyzxyzxyz"})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["data"] == []

    def test_sem_search_retorna_todos(self, auth_client, db):
        Produtor.objects.create(nome="Produtor A")
        Produtor.objects.create(nome="Produtor B")
        resp = auth_client.get(reverse("produtor-list-create"))
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["data"]) == 2


# ─── Recebimento ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProdutorRecebimento:
    """Valores aceitos: lucro, comissao, premio ou vazio."""

    @pytest.mark.parametrize("recebimento", ["lucro", "comissao", "premio", ""])
    def test_recebimento_valido(self, auth_client, db, recebimento):
        resp = auth_client.post(
            reverse("produtor-list-create"),
            {"nome": f"Produtor {recebimento}", "recebimento": recebimento},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["data"]["recebimento"] == recebimento

    def test_recebimento_invalido_retorna_400(self, auth_client, db):
        resp = auth_client.post(
            reverse("produtor-list-create"),
            {"nome": "Produtor Inválido", "recebimento": "transferencia"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
