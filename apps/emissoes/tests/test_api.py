"""Testes dos endpoints do wizard."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.emissoes.conectores.base import (
    ErroValidacaoSeguradora,
    SeguradoraIndisponivel,
)
from apps.emissoes.models import EmissaoSeguradora
from apps.emissoes.services import emissao_cotar

from .conftest import ConectorFake

User = get_user_model()


@pytest.fixture
def cliente(db):
    usuario = User.objects.create_user(email="op@cajuina.com.br", password="x")
    api = APIClient()
    api.force_authenticate(user=usuario)
    return api


@pytest.fixture
def conector_fake(monkeypatch):
    """O service importa `get_conector` para o próprio namespace."""
    fake = ConectorFake()
    monkeypatch.setattr(
        "apps.emissoes.services.get_conector", lambda seguradora, **kw: fake
    )
    return fake


@pytest.mark.django_db
class TestEstado:
    def test_devolve_a_lista_sem_tocar_na_seguradora(
        self, cliente, cotacao, conector_fake
    ):
        emissao_cotar(
            cotacao_id=cotacao.pk,
            seguradora_id=cotacao.seguradora_id,
            conector=ConectorFake(),
        )

        url = reverse("cotacao-emissao", args=[cotacao.pk])
        resposta = cliente.get(url)

        assert resposta.status_code == status.HTTP_200_OK
        assert len(resposta.data["data"]) == 1
        assert resposta.data["data"][0]["etapa"] == EmissaoSeguradora.ETAPA_COTADA
        assert resposta.data["data"][0]["external_id"] == "2601513"
        assert conector_fake.chamadas == []

    def test_devolve_lista_vazia_quando_ainda_nao_cotou(self, cliente, cotacao):
        url = reverse("cotacao-emissao", args=[cotacao.pk])
        resposta = cliente.get(url)

        assert resposta.status_code == status.HTTP_200_OK
        assert resposta.data == {"data": []}

    def test_nao_expoe_o_payload_cru_da_seguradora(self, cliente, cotacao):
        emissao_cotar(
            cotacao_id=cotacao.pk,
            seguradora_id=cotacao.seguradora_id,
            conector=ConectorFake(),
        )

        resposta = cliente.get(reverse("cotacao-emissao", args=[cotacao.pk]))

        assert "ultimo_request" not in resposta.data["data"][0]
        assert "ultima_resposta" not in resposta.data["data"][0]

    def test_sem_token_e_401(self, cotacao):
        resposta = APIClient().get(reverse("cotacao-emissao", args=[cotacao.pk]))
        assert resposta.status_code == status.HTTP_401_UNAUTHORIZED

    def test_cotacao_inexistente_e_404(self, cliente, db):
        resposta = cliente.get(reverse("cotacao-emissao", args=[99999]))
        assert resposta.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestCotar:
    def _post(self, cliente, cotacao, seguradora_id):
        return cliente.post(
            reverse("cotacao-emissao-cotar", args=[cotacao.pk]),
            {"seguradora": seguradora_id},
            format="json",
        )

    def test_cota_e_devolve_o_estado_envelopado(
        self, cliente, cotacao, seguradora, conector_fake
    ):
        resposta = self._post(cliente, cotacao, seguradora.pk)

        assert resposta.status_code == status.HTTP_200_OK
        dados = resposta.data["data"]
        assert dados["etapa"] == EmissaoSeguradora.ETAPA_COTADA
        assert dados["premio_total"] == "500.00"
        assert dados["numero_max_parcelas"] == 3
        assert len(dados["opcoes_parcelamento"]) == 1
        assert [c[0] for c in conector_fake.chamadas] == ["cotar"]

    def test_post_e_get_devolvem_o_mesmo_parcelamento(
        self, cliente, cotacao, seguradora, conector_fake
    ):
        """O POST serializa o objeto em memória e o GET o que veio do banco.

        Sem a conversão explícita em `_opcoes_para_json`, o mesmo campo saía
        como número num e como string no outro, e o front quebrava conforme a
        rota que tivesse chamado.
        """
        do_post = self._post(cliente, cotacao, seguradora.pk)
        do_get = cliente.get(reverse("cotacao-emissao", args=[cotacao.pk]))

        assert (
            do_post.data["data"]["opcoes_parcelamento"]
            == do_get.data["data"][0]["opcoes_parcelamento"]
        )
        parcela = do_get.data["data"][0]["opcoes_parcelamento"][0]["parcelas"][0]
        assert parcela["valor"] == "500.00"

    def test_sem_seguradora_no_body_e_400(self, cliente, cotacao, conector_fake):
        resposta = cliente.post(
            reverse("cotacao-emissao-cotar", args=[cotacao.pk]), {}, format="json"
        )

        assert resposta.status_code == status.HTTP_400_BAD_REQUEST
        assert "seguradora" in resposta.data["detail"].lower()
        assert conector_fake.chamadas == []

    def test_seguradora_inexistente_e_404(self, cliente, cotacao, conector_fake):
        resposta = self._post(cliente, cotacao, 99999)

        assert resposta.status_code == status.HTTP_404_NOT_FOUND
        assert conector_fake.chamadas == []

    def test_sem_token_e_401(self, cotacao, seguradora):
        resposta = APIClient().post(
            reverse("cotacao-emissao-cotar", args=[cotacao.pk]),
            {"seguradora": seguradora.pk},
            format="json",
        )
        assert resposta.status_code == status.HTTP_401_UNAUTHORIZED

    def test_cotacao_inexistente_e_404(self, cliente, db, seguradora):
        resposta = cliente.post(
            reverse("cotacao-emissao-cotar", args=[99999]),
            {"seguradora": seguradora.pk},
            format="json",
        )
        assert resposta.status_code == status.HTTP_404_NOT_FOUND

    def test_erro_de_validacao_nosso_e_400(self, cliente, cotacao, seguradora):
        seguradora.integracao = ""
        seguradora.save()

        resposta = self._post(cliente, cotacao, seguradora.pk)

        assert resposta.status_code == status.HTTP_400_BAD_REQUEST
        assert "emissão manual" in resposta.data["detail"]

    def test_mensagem_da_seguradora_chega_ao_usuario(
        self, cliente, cotacao, seguradora, monkeypatch
    ):
        def recusa(*args, **kwargs):
            raise ErroValidacaoSeguradora("Limite insuficiente para o tomador.")

        monkeypatch.setattr("apps.emissoes.services.get_conector", recusa)

        resposta = self._post(cliente, cotacao, seguradora.pk)

        assert resposta.status_code == status.HTTP_400_BAD_REQUEST
        assert resposta.data["detail"] == "Limite insuficiente para o tomador."

    def test_seguradora_fora_do_ar_e_502(
        self, cliente, cotacao, seguradora, monkeypatch
    ):
        def cai(*args, **kwargs):
            raise SeguradoraIndisponivel("A seguradora não respondeu. Tente novamente.")

        monkeypatch.setattr("apps.emissoes.services.get_conector", cai)

        resposta = self._post(cliente, cotacao, seguradora.pk)

        assert resposta.status_code == status.HTTP_502_BAD_GATEWAY
        assert "não respondeu" in resposta.data["detail"]

    def test_nao_grava_emissao_quando_a_seguradora_falha(
        self, cliente, cotacao, seguradora, monkeypatch
    ):
        def cai(*args, **kwargs):
            raise SeguradoraIndisponivel("fora do ar")

        monkeypatch.setattr("apps.emissoes.services.get_conector", cai)
        self._post(cliente, cotacao, seguradora.pk)

        assert not EmissaoSeguradora.objects.exists()


@pytest.mark.django_db
class TestSegredosDaSeguradora:
    def test_get_de_seguradoras_nao_devolve_segredo(self, cliente, seguradora):
        seguradora.api_senha = "senha-da-v1"
        seguradora.save()

        resposta = cliente.get("/api/v1/seguradoras/")

        assert resposta.status_code == status.HTTP_200_OK
        corpo = resposta.json()["data"][0]
        assert "api_client_secret" not in corpo
        assert "api_senha" not in corpo
        # o front precisa saber que existe credencial, sem receber o segredo
        assert corpo["tem_credencial_api"] is True
        assert corpo["api_client_id"] == "cid"

    def test_segredo_continua_gravavel(self, cliente, seguradora):
        resposta = cliente.patch(
            f"/api/v1/seguradoras/{seguradora.pk}/",
            {"api_client_secret": "novo-segredo"},
            format="json",
        )

        assert resposta.status_code == status.HTTP_200_OK
        seguradora.refresh_from_db()
        assert seguradora.api_client_secret == "novo-segredo"
