import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.apolices.models import Apolice
from apps.cotacoes.models import Cotacao
from apps.modalidades.models import Modalidade
from apps.seguradoras.models import Seguradora
from apps.tomadores.models import Tomador

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
    resp = client.post(
        reverse("token_obtain_pair"),
        {"username": "tester", "password": "senha123"},
        format="json",
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")
    return client


@pytest.fixture
def modalidade(db):
    return Modalidade.objects.create(nome="Garantia")


@pytest.fixture
def seguradora(db):
    return Seguradora.objects.create(nome="Alfa Seguros", premio_minimo="500.00")


@pytest.fixture
def tomador(db):
    return Tomador.objects.create(cnpj="12.345.678/0001-90", nome="Construtora Teste")


@pytest.fixture
def cotacao(db, tomador, modalidade):
    return Cotacao.objects.create(
        tomador=tomador, modalidade=modalidade, status=Cotacao.STATUS_EMITIDO
    )


@pytest.fixture
def apolice(db, cotacao, seguradora):
    return Apolice.objects.create(
        cotacao=cotacao,
        seguradora=seguradora,
        numero_apolice="A1",
        valor_seguradora="100.00",
    )


# ─── Filtro por tomador na listagem ──────────────────────────────────────────


@pytest.mark.django_db
class TestApoliceListFiltroTomador:
    def test_filtra_pelo_tomador(
        self, auth_client, apolice, tomador, modalidade, seguradora
    ):
        outro = Tomador.objects.create(cnpj="99.888.777/0001-66", nome="Outra Empresa")
        cotacao_outro = Cotacao.objects.create(
            tomador=outro, modalidade=modalidade, status=Cotacao.STATUS_EMITIDO
        )
        Apolice.objects.create(
            cotacao=cotacao_outro,
            seguradora=seguradora,
            numero_apolice="B1",
            valor_seguradora="900.00",
        )

        resp = auth_client.get(reverse("apolice-list"), {"tomador": tomador.pk})
        numeros = [a["numero_apolice"] for a in resp.data["data"]]

        assert resp.status_code == status.HTTP_200_OK
        assert numeros == ["A1"]

    def test_tomador_nao_numerico_e_ignorado(self, auth_client, apolice):
        resp = auth_client.get(reverse("apolice-list"), {"tomador": "abc"})
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["data"]) == 1


# ─── PATCH ───────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestApoliceUpdate:
    def test_exige_autenticacao(self, client, apolice):
        resp = client.patch(
            reverse("apolice-detail", args=[apolice.pk]),
            {"numero_apolice": "X"},
            format="json",
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_atualiza_campos_editaveis(self, auth_client, apolice):
        resp = auth_client.patch(
            reverse("apolice-detail", args=[apolice.pk]),
            {"numero_apolice": "A1-RETIFICADA", "observacoes": "corrigido"},
            format="json",
        )

        apolice.refresh_from_db()
        assert resp.status_code == status.HTTP_200_OK
        assert apolice.numero_apolice == "A1-RETIFICADA"
        assert apolice.observacoes == "corrigido"

    def test_nao_troca_a_cotacao(self, auth_client, apolice, modalidade):
        """`cotacao` é read-only no serializer — o vínculo não pode ser remanejado."""
        outro = Tomador.objects.create(cnpj="99.888.777/0001-66", nome="Outra Empresa")
        outra_cotacao = Cotacao.objects.create(tomador=outro, modalidade=modalidade)
        cotacao_original = apolice.cotacao_id

        auth_client.patch(
            reverse("apolice-detail", args=[apolice.pk]),
            {"cotacao": outra_cotacao.pk},
            format="json",
        )

        apolice.refresh_from_db()
        assert apolice.cotacao_id == cotacao_original

    def test_apolice_inexistente_retorna_404(self, auth_client):
        resp = auth_client.patch(
            reverse("apolice-detail", args=[9999]),
            {"numero_apolice": "X"},
            format="json",
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ─── DELETE ──────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestApoliceDelete:
    def test_exige_autenticacao(self, client, apolice):
        resp = client.delete(reverse("apolice-detail", args=[apolice.pk]))
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_remove_a_apolice(self, auth_client, apolice):
        resp = auth_client.delete(reverse("apolice-detail", args=[apolice.pk]))

        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not Apolice.objects.filter(pk=apolice.pk).exists()

    def test_devolve_a_cotacao_para_aprovada(self, auth_client, apolice, cotacao):
        """Inverso de `apolice_emitir`: a cotação volta a poder ser reemitida."""
        auth_client.delete(reverse("apolice-detail", args=[apolice.pk]))

        cotacao.refresh_from_db()
        assert cotacao.status == Cotacao.STATUS_APROVADO

    def test_apolice_inexistente_retorna_404(self, auth_client):
        resp = auth_client.delete(reverse("apolice-detail", args=[9999]))
        assert resp.status_code == status.HTTP_404_NOT_FOUND
