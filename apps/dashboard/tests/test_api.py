from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from apps.apolices.models import Apolice
from apps.cotacoes.models import Cotacao
from apps.modalidades.models import Modalidade
from apps.seguradoras.models import Seguradora
from apps.tomadores.models import Tomador

User = get_user_model()


@pytest.fixture
def usuario(db):
    return User.objects.create_user(
        email="tester@empresa.com", password="senha123", first_name="Tester"
    )


@pytest.fixture
def auth_client(usuario):
    client = APIClient()
    resp = client.post(
        reverse("token_obtain_pair"),
        {"email": "tester@empresa.com", "password": "senha123"},
        format="json",
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")
    return client


@pytest.fixture
def dados(db, usuario):
    seguradora = Seguradora.objects.create(
        nome="AVLA", premio_minimo=Decimal("100.00"),
        taxa_comissao=Decimal("10.00"), meta=Decimal("10000.00"),
    )
    modalidade = Modalidade.objects.create(nome="Garantia")
    tomador = Tomador.objects.create(
        cnpj="11.111.111/0001-11", nome="ACME", contato="João",
        telefone="(85) 98888-0000", email="acme@teste.com", criado_por=usuario,
    )
    cotacao = Cotacao.objects.create(
        status=Cotacao.STATUS_EMITIDO, tomador=tomador, modalidade=modalidade,
        seguradora=seguradora, premio=Decimal("1000.00"),
    )
    Apolice.objects.create(
        cotacao=cotacao, seguradora=seguradora, numero_apolice="AP-1",
        valor_seguradora=Decimal("900.00"),
    )
    return {"seguradora": seguradora, "tomador": tomador}


@pytest.mark.django_db
class TestResumoEndpoint:
    def test_sem_token_retorna_401(self):
        resp = APIClient().get(reverse("dashboard-resumo"))

        assert resp.status_code == 401

    def test_contrato_da_resposta(self, auth_client, dados):
        resp = auth_client.get(reverse("dashboard-resumo"))

        assert resp.status_code == 200
        data = resp.data["data"]
        assert set(data.keys()) == {"producao", "apolices", "tomadores", "cotacoes", "periodo"}
        assert set(data["tomadores"].keys()) == {"periodo", "total"}
        assert set(data["cotacoes"].keys()) == {"iniciadas", "aprovadas", "emitidas"}
        assert set(data["periodo"].keys()) == {"tipo", "inicio", "fim", "rotulo"}

    def test_periodo_padrao_e_mes(self, auth_client, dados):
        resp = auth_client.get(reverse("dashboard-resumo"))

        assert resp.data["data"]["periodo"]["tipo"] == "mes"

    def test_aceita_periodo_dia(self, auth_client, dados):
        resp = auth_client.get(reverse("dashboard-resumo"), {"periodo": "dia"})

        assert resp.data["data"]["periodo"]["tipo"] == "dia"

    def test_periodo_invalido_cai_para_mes(self, auth_client, dados):
        resp = auth_client.get(reverse("dashboard-resumo"), {"periodo": "decada"})

        assert resp.status_code == 200
        assert resp.data["data"]["periodo"]["tipo"] == "mes"


@pytest.mark.django_db
class TestComissoesEndpoint:
    def test_sem_token_retorna_401(self):
        resp = APIClient().get(reverse("dashboard-comissoes"))

        assert resp.status_code == 401

    def test_contrato_da_resposta(self, auth_client, dados):
        resp = auth_client.get(reverse("dashboard-comissoes"))

        assert resp.status_code == 200
        assert set(resp.data["data"].keys()) == {"a_receber", "pago", "em_atraso", "a_pagar"}


@pytest.mark.django_db
class TestPremioSeguradorasEndpoint:
    def test_sem_token_retorna_401(self):
        resp = APIClient().get(reverse("dashboard-premio-seguradoras"))

        assert resp.status_code == 401

    def test_contrato_da_resposta(self, auth_client, dados):
        resp = auth_client.get(reverse("dashboard-premio-seguradoras"))

        assert resp.status_code == 200
        linha = resp.data["data"][0]
        assert set(linha.keys()) == {"id", "seguradora", "valor_atual", "meta", "falta"}

    def test_ano_invalido_cai_para_o_ano_corrente(self, auth_client, dados):
        resp = auth_client.get(reverse("dashboard-premio-seguradoras"), {"ano": "abc"})

        assert resp.status_code == 200


@pytest.mark.django_db
class TestNovosCadastrosEndpoint:
    def test_sem_token_retorna_401(self):
        resp = APIClient().get(reverse("dashboard-novos-cadastros"))

        assert resp.status_code == 401

    def test_contrato_da_resposta(self, auth_client, dados):
        resp = auth_client.get(reverse("dashboard-novos-cadastros"))

        assert resp.status_code == 200
        data = resp.data["data"]
        assert set(data.keys()) == {"results", "count", "page", "page_size"}
        assert data["results"][0]["criado_por"] == "Tester"

    def test_busca(self, auth_client, dados):
        resp = auth_client.get(reverse("dashboard-novos-cadastros"), {"search": "ACME"})

        assert resp.data["data"]["count"] == 1

    def test_busca_sem_resultado(self, auth_client, dados):
        resp = auth_client.get(reverse("dashboard-novos-cadastros"), {"search": "zzz"})

        assert resp.data["data"]["count"] == 0
        assert resp.data["data"]["results"] == []

    def test_page_invalida_cai_para_1(self, auth_client, dados):
        resp = auth_client.get(reverse("dashboard-novos-cadastros"), {"page": "abc"})

        assert resp.status_code == 200
        assert resp.data["data"]["page"] == 1


@pytest.mark.django_db
class TestSerializacaoDeValores:
    """Dinheiro sai como string, não como float — evita erro de arredondamento."""

    def test_producao_e_string(self, auth_client, dados):
        resp = auth_client.get(reverse("dashboard-resumo"))

        assert resp.data["data"]["producao"] == "1000.00"

    def test_comissoes_sao_strings(self, auth_client, dados):
        resp = auth_client.get(reverse("dashboard-comissoes"))

        for valor in resp.data["data"].values():
            assert isinstance(valor, str), f"esperava string, veio {type(valor)}"

    def test_valores_do_grafico_sao_strings(self, auth_client, dados):
        resp = auth_client.get(reverse("dashboard-premio-seguradoras"))

        linha = resp.data["data"][0]
        assert isinstance(linha["valor_atual"], str)
        assert isinstance(linha["meta"], str)
        assert isinstance(linha["falta"], str)

    def test_meta_nula_continua_nula(self, auth_client, dados):
        dados["seguradora"].meta = None
        dados["seguradora"].save()

        resp = auth_client.get(reverse("dashboard-premio-seguradoras"))

        assert resp.data["data"][0]["meta"] is None
        assert resp.data["data"][0]["falta"] is None

    def test_contagens_continuam_inteiras(self, auth_client, dados):
        resp = auth_client.get(reverse("dashboard-resumo"))

        assert resp.data["data"]["apolices"] == 1
        assert resp.data["data"]["tomadores"]["total"] == 1
