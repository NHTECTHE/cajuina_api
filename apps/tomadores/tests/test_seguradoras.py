import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.seguradoras.models import Seguradora
from apps.tomadores.models import Tomador, TomadorSeguradora

User = get_user_model()

# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(email="tester@empresa.com", password="senha123")


@pytest.fixture
def auth_client(client, user):
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
def porto(db):
    return Seguradora.objects.create(
        nome="Porto Seguro", premio_minimo="150.00", vencimento_dias=30
    )


@pytest.fixture
def junto(db):
    return Seguradora.objects.create(
        nome="Junto Seguros", premio_minimo="140.00", vencimento_dias=20
    )


# ─── Autenticação ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestAutenticacao:
    def test_listar_sem_token_retorna_401(self, client, tomador):
        resp = client.get(reverse("tomador-seguradora-list", args=[tomador.pk]))
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_salvar_sem_token_retorna_401(self, client, tomador):
        resp = client.put(
            reverse("tomador-seguradora-list", args=[tomador.pk]),
            {"itens": []},
            format="json",
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# ─── Model ────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestModel:
    def test_par_duplicado_viola_constraint(self, tomador, porto):
        TomadorSeguradora.objects.create(tomador=tomador, seguradora=porto, taxa="1.50")
        with pytest.raises(IntegrityError):
            TomadorSeguradora.objects.create(
                tomador=tomador, seguradora=porto, taxa="2.00"
            )

    def test_taxa_zero_deixa_inapto(self, tomador, porto):
        vinculo = TomadorSeguradora.objects.create(
            tomador=tomador, seguradora=porto, taxa=0
        )
        assert vinculo.apto is False

    def test_taxa_positiva_habilita(self, tomador, porto):
        vinculo = TomadorSeguradora.objects.create(
            tomador=tomador,
            seguradora=porto,
            taxa="1.50",
            status=TomadorSeguradora.Status.CADASTRO_OK,
        )
        assert vinculo.apto is True

    def test_taxa_positiva_sem_cadastro_ok_deixa_inapto(self, tomador, porto):
        vinculo = TomadorSeguradora.objects.create(
            tomador=tomador, seguradora=porto, taxa="1.50"
        )
        assert vinculo.status == TomadorSeguradora.Status.SEM_CADASTRO
        assert vinculo.apto is False

    def test_premio_minimo_nulo_herda_da_seguradora(self, tomador, porto):
        vinculo = TomadorSeguradora.objects.create(
            tomador=tomador, seguradora=porto, taxa="1.50", premio_minimo=None
        )
        assert vinculo.premio_minimo_efetivo == porto.premio_minimo

    def test_premio_minimo_do_par_sobrepoe_o_da_seguradora(self, tomador, porto):
        vinculo = TomadorSeguradora.objects.create(
            tomador=tomador, seguradora=porto, taxa="1.50", premio_minimo="90.00"
        )
        assert str(vinculo.premio_minimo_efetivo) == "90.00"

    def test_dias_vencimento_nulo_herda_da_seguradora(self, tomador, porto):
        vinculo = TomadorSeguradora.objects.create(
            tomador=tomador, seguradora=porto, taxa="1.50", dias_vencimento=None
        )
        assert vinculo.dias_vencimento_efetivo == porto.vencimento_dias

    def test_dias_vencimento_do_par_sobrepoe_o_da_seguradora(self, tomador, porto):
        vinculo = TomadorSeguradora.objects.create(
            tomador=tomador, seguradora=porto, taxa="1.50", dias_vencimento=45
        )
        assert vinculo.dias_vencimento_efetivo == 45


# ─── Listagem ─────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestListagem:
    def test_lista_vazia_quando_sem_vinculos(self, auth_client, tomador):
        resp = auth_client.get(reverse("tomador-seguradora-list", args=[tomador.pk]))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["data"] == []

    def test_lista_traz_nome_da_seguradora(self, auth_client, tomador, porto):
        TomadorSeguradora.objects.create(tomador=tomador, seguradora=porto, taxa="1.50")
        resp = auth_client.get(reverse("tomador-seguradora-list", args=[tomador.pk]))
        assert resp.data["data"][0]["seguradora_nome"] == "Porto Seguro"

    def test_aptas_exclui_taxa_zero(self, auth_client, tomador, porto, junto):
        TomadorSeguradora.objects.create(tomador=tomador, seguradora=porto, taxa="1.50")
        TomadorSeguradora.objects.create(tomador=tomador, seguradora=junto, taxa=0)

        resp = auth_client.get(
            reverse("tomador-seguradora-list", args=[tomador.pk]), {"aptas": "true"}
        )
        nomes = [item["seguradora_nome"] for item in resp.data["data"]]
        assert nomes == ["Porto Seguro"]

    def test_aptas_exclui_seguradora_inativa(self, auth_client, tomador, porto, junto):
        junto.ativo = False
        junto.save()
        TomadorSeguradora.objects.create(tomador=tomador, seguradora=porto, taxa="1.50")
        TomadorSeguradora.objects.create(tomador=tomador, seguradora=junto, taxa="2.25")

        resp = auth_client.get(
            reverse("tomador-seguradora-list", args=[tomador.pk]), {"aptas": "true"}
        )
        nomes = [item["seguradora_nome"] for item in resp.data["data"]]
        assert nomes == ["Porto Seguro"]

    def test_sem_filtro_traz_inaptas_tambem(self, auth_client, tomador, porto, junto):
        TomadorSeguradora.objects.create(tomador=tomador, seguradora=porto, taxa="1.50")
        TomadorSeguradora.objects.create(tomador=tomador, seguradora=junto, taxa=0)

        resp = auth_client.get(reverse("tomador-seguradora-list", args=[tomador.pk]))
        assert len(resp.data["data"]) == 2

    def test_nao_vaza_vinculo_de_outro_tomador(self, auth_client, tomador, porto):
        outro = Tomador.objects.create(cnpj="98.765.432/0001-10", nome="Outra")
        TomadorSeguradora.objects.create(tomador=outro, seguradora=porto, taxa="3.00")

        resp = auth_client.get(reverse("tomador-seguradora-list", args=[tomador.pk]))
        assert resp.data["data"] == []

    def test_tomador_inexistente_retorna_404(self, auth_client):
        resp = auth_client.get(reverse("tomador-seguradora-list", args=[9999]))
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ─── Gravação em lote ─────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestBulkUpsert:
    def test_cria_vinculos(self, auth_client, tomador, porto, junto):
        payload = {
            "itens": [
                {"seguradora": porto.pk, "taxa": "1.50"},
                {"seguradora": junto.pk, "taxa": "2.25"},
            ]
        }
        resp = auth_client.put(
            reverse("tomador-seguradora-list", args=[tomador.pk]),
            payload,
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert TomadorSeguradora.objects.filter(tomador=tomador).count() == 2

    def test_upsert_e_idempotente(self, auth_client, tomador, porto):
        payload = {"itens": [{"seguradora": porto.pk, "taxa": "1.50"}]}
        url = reverse("tomador-seguradora-list", args=[tomador.pk])

        auth_client.put(url, payload, format="json")
        auth_client.put(url, payload, format="json")

        assert TomadorSeguradora.objects.filter(tomador=tomador).count() == 1

    def test_regravar_atualiza_a_taxa(self, auth_client, tomador, porto):
        url = reverse("tomador-seguradora-list", args=[tomador.pk])
        auth_client.put(
            url, {"itens": [{"seguradora": porto.pk, "taxa": "1.50"}]}, format="json"
        )
        auth_client.put(
            url, {"itens": [{"seguradora": porto.pk, "taxa": "3.00"}]}, format="json"
        )

        vinculo = TomadorSeguradora.objects.get(tomador=tomador, seguradora=porto)
        assert str(vinculo.taxa) == "3.00"

    def test_seguradora_fora_do_payload_fica_intacta(
        self, auth_client, tomador, porto, junto
    ):
        TomadorSeguradora.objects.create(tomador=tomador, seguradora=junto, taxa="2.25")

        auth_client.put(
            reverse("tomador-seguradora-list", args=[tomador.pk]),
            {"itens": [{"seguradora": porto.pk, "taxa": "1.50"}]},
            format="json",
        )

        vinculo = TomadorSeguradora.objects.get(tomador=tomador, seguradora=junto)
        assert str(vinculo.taxa) == "2.25"

    def test_seguradora_repetida_retorna_400(self, auth_client, tomador, porto):
        payload = {
            "itens": [
                {"seguradora": porto.pk, "taxa": "1.50"},
                {"seguradora": porto.pk, "taxa": "2.00"},
            ]
        }
        resp = auth_client.put(
            reverse("tomador-seguradora-list", args=[tomador.pk]),
            payload,
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_taxa_negativa_retorna_400(self, auth_client, tomador, porto):
        resp = auth_client.put(
            reverse("tomador-seguradora-list", args=[tomador.pk]),
            {"itens": [{"seguradora": porto.pk, "taxa": "-1.00"}]},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_lote_invalido_nao_grava_nada(self, auth_client, tomador, porto, junto):
        """A transação atômica desfaz o lote inteiro se um item falhar."""
        payload = {
            "itens": [
                {"seguradora": porto.pk, "taxa": "1.50"},
                {"seguradora": junto.pk, "taxa": "-2.00"},
            ]
        }
        auth_client.put(
            reverse("tomador-seguradora-list", args=[tomador.pk]),
            payload,
            format="json",
        )
        assert TomadorSeguradora.objects.filter(tomador=tomador).count() == 0


# ─── Item individual ──────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestDetalhe:
    def test_put_cria_quando_nao_existe(self, auth_client, tomador, porto):
        resp = auth_client.put(
            reverse("tomador-seguradora-detail", args=[tomador.pk, porto.pk]),
            {"taxa": "1.50"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert TomadorSeguradora.objects.filter(
            tomador=tomador, seguradora=porto
        ).exists()

    def test_zerar_taxa_desabilita(self, auth_client, tomador, porto):
        url = reverse("tomador-seguradora-detail", args=[tomador.pk, porto.pk])
        auth_client.put(url, {"taxa": "1.50"}, format="json")

        resp = auth_client.put(url, {"taxa": "0"}, format="json")
        assert resp.data["data"]["apto"] is False

    def test_preencher_taxa_reabilita(self, auth_client, tomador, porto):
        url = reverse("tomador-seguradora-detail", args=[tomador.pk, porto.pk])
        auth_client.put(url, {"taxa": "0", "status": "cadastro_ok"}, format="json")

        resp = auth_client.put(
            url, {"taxa": "2.00", "status": "cadastro_ok"}, format="json"
        )
        assert resp.data["data"]["apto"] is True

    def test_get_de_vinculo_inexistente_retorna_404(self, auth_client, tomador, porto):
        resp = auth_client.get(
            reverse("tomador-seguradora-detail", args=[tomador.pk, porto.pk])
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_remove_o_vinculo(self, auth_client, tomador, porto):
        TomadorSeguradora.objects.create(tomador=tomador, seguradora=porto, taxa="1.50")

        resp = auth_client.delete(
            reverse("tomador-seguradora-detail", args=[tomador.pk, porto.pk])
        )
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not TomadorSeguradora.objects.filter(tomador=tomador).exists()

    def test_excluir_tomador_remove_vinculos_em_cascata(self, tomador, porto):
        TomadorSeguradora.objects.create(tomador=tomador, seguradora=porto, taxa="1.50")
        tomador.delete()
        assert TomadorSeguradora.objects.count() == 0
