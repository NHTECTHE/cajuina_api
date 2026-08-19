"""Passo 2 da emissão: segurado na Junto e geração da minuta.

As respostas são as que o sandbox devolveu em 18/08/2026 — não exemplos
inventados a partir do swagger. Segue o padrão de `test_conector_junto.py`:
seguradora falsa em memória e cache de token limpo entre os testes.
"""

import json

import httpx
import pytest

from apps.emissoes.conectores.base import DadosSegurado, SeguradoJunto
from apps.emissoes.conectores.junto import ConectorJunto, limpar_cache_token


class SeguradoraFake:
    """O conector só precisa de pk, credenciais e ambiente — não do model."""

    def __init__(self, *, pk=1, ambiente="sandbox", client_id="cid", secret="segredo"):
        self.pk = pk
        self.api_ambiente = ambiente
        self.api_client_id = client_id
        self.api_client_secret = secret


@pytest.fixture(autouse=True)
def _cache_limpo():
    limpar_cache_token()
    yield
    limpar_cache_token()


TOKEN = httpx.Response(
    200, json={"accessToken": "t", "expiresIn": 3600, "tokenType": "Bearer"}
)


def _conector(rotas):
    """Conector com transporte falso. `rotas` mapeia (método, sufixo) -> resposta."""

    def handler(request: httpx.Request) -> httpx.Response:
        for (metodo, sufixo), resposta in rotas.items():
            if request.method == metodo and request.url.path.endswith(sufixo):
                return resposta
        return httpx.Response(404, json=[{"message": "rota não mapeada"}])

    return ConectorJunto(SeguradoraFake(), transport=httpx.MockTransport(handler))


class TestBuscarSegurado:
    def test_devolve_ids_quando_encontra(self):
        con = _conector(
            {
                ("POST", "/authentication"): TOKEN,
                ("GET", "/insured"): httpx.Response(
                    200,
                    json=[
                        {
                            "id": 126852,
                            "name": "PREFEITURA CAMPO MOURAO",
                            "address": [{"addressId": 150755}],
                        }
                    ],
                ),
            }
        )

        achado = con.buscar_segurado(federal_id="22333444000166")

        assert achado is not None
        assert achado.insured_id == 126852
        assert achado.address_id == 150755

    def test_devolve_none_quando_lista_vazia(self):
        con = _conector(
            {
                ("POST", "/authentication"): TOKEN,
                ("GET", "/insured"): httpx.Response(200, json=[]),
            }
        )

        assert con.buscar_segurado(federal_id="22333444000166") is None

    def test_manda_o_cnpj_na_query(self):
        vistos = {}

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/authentication"):
                return TOKEN
            vistos["query"] = str(request.url.query, "utf-8")
            return httpx.Response(200, json=[])

        con = ConectorJunto(SeguradoraFake(), transport=httpx.MockTransport(handler))
        con.buscar_segurado(federal_id="22333444000166")

        assert vistos["query"] == "federalId=22333444000166"


class TestCadastrarSegurado:
    def test_envia_o_payload_que_a_junto_exige(self):
        enviados = {}

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/authentication"):
                return TOKEN
            enviados["corpo"] = json.loads(request.content)
            return httpx.Response(
                200, json={"id": 999, "address": [{"addressId": 111}]}
            )

        con = ConectorJunto(SeguradoraFake(), transport=httpx.MockTransport(handler))

        criado = con.cadastrar_segurado(
            dados=DadosSegurado(
                federal_id="22.333.444/0001-66",
                nome="COMERCIO VERDE ALIMENTOS LTDA",
                tipo=9,
                logradouro="RUA DAS FLORES 100",
                cidade="FORTALEZA",
                uf="CE",
                cep="60000-000",
            )
        )

        assert criado == SeguradoJunto(insured_id=999, address_id=111)
        corpo = enviados["corpo"]
        # CNPJ e CEP vão só com dígitos, como a Junto exige.
        assert corpo["federalId"] == "22333444000166"
        assert corpo["address"]["zipCode"] == "60000000"
        assert corpo["insuredType"] == 9
        assert corpo["address"]["city"] == "FORTALEZA"
        assert corpo["address"]["state"] == "CE"


MINUTA_COM_PENDENCIA = httpx.Response(
    200,
    json={
        "policyContacts": [],
        "documentNumber": 6497972,
        "draftUrl": "",
        "hasHangs": True,
        "isForceDraftUrl": False,
    },
)

HANGS = httpx.Response(
    200,
    json=[
        {
            "code": 12,
            "description": "Fora dos parâmetros de crédito. ",
            "department": {
                "id": 3,
                "name": "Crédito - Crédito",
                "email": "plataforma@juntoseguros.com",
            },
        },
        {
            "code": 17,
            "description": "Pendência financeira tomador. ",
            "department": {
                "id": 2,
                "name": "Comercial - CE",
                "email": "segcomercialce@jmsegs.com",
            },
        },
    ],
)


class TestGerarMinuta:
    def test_traz_as_pendencias_quando_a_minuta_sai_sem_url(self):
        con = _conector(
            {
                ("POST", "/authentication"): TOKEN,
                ("PUT", "/draft"): MINUTA_COM_PENDENCIA,
                ("GET", "/hangs"): HANGS,
            }
        )

        r = con.gerar_minuta(
            external_id="2601519",
            edital="TESTE-AO-VIVO-2",
            segurado=SeguradoJunto(insured_id=126852, address_id=150755),
        )

        assert r.document_number == "6497972"
        assert r.url_minuta == ""
        assert r.tem_pendencias is True
        assert len(r.pendencias) == 2
        assert r.pendencias[0].codigo == 12
        # a Junto manda espaço sobrando no fim da descrição
        assert r.pendencias[0].descricao == "Fora dos parâmetros de crédito."
        assert r.pendencias[1].departamento == "Comercial - CE"
        assert r.pendencias[1].email == "segcomercialce@jmsegs.com"

    def test_nao_consulta_pendencias_quando_nao_ha(self):
        chamadas = []

        def handler(request: httpx.Request) -> httpx.Response:
            chamadas.append(request.url.path)
            if request.url.path.endswith("/authentication"):
                return TOKEN
            return httpx.Response(
                200,
                json={
                    "documentNumber": 1,
                    "draftUrl": "https://junto/minuta.pdf",
                    "hasHangs": False,
                },
            )

        con = ConectorJunto(SeguradoraFake(), transport=httpx.MockTransport(handler))

        r = con.gerar_minuta(
            external_id="1",
            edital="E",
            segurado=SeguradoJunto(insured_id=1, address_id=1),
        )

        assert r.tem_pendencias is False
        assert r.url_minuta == "https://junto/minuta.pdf"
        assert not any("hangs" in c for c in chamadas)

    def test_forcar_url_vai_no_payload(self):
        enviados = {}

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/authentication"):
                return TOKEN
            if request.url.path.endswith("/draft"):
                enviados["corpo"] = json.loads(request.content)
                return httpx.Response(
                    200,
                    json={
                        "documentNumber": 2,
                        "draftUrl": "https://junto/forcada.pdf",
                        "hasHangs": True,
                    },
                )
            return HANGS

        con = ConectorJunto(SeguradoraFake(), transport=httpx.MockTransport(handler))

        r = con.gerar_minuta(
            external_id="2",
            edital="EDITAL-1",
            segurado=SeguradoJunto(insured_id=1, address_id=2),
            forcar_url=True,
        )

        corpo = enviados["corpo"]
        assert corpo["isForceDraftUrl"] is True
        assert corpo["publicNoticeOrContract"] == "EDITAL-1"
        # o bloco insured não é opcional: sem ele a Junto devolve 500
        assert corpo["insured"] == {"insuredId": 1, "insuredAddressId": 2}
        assert r.url_minuta == "https://junto/forcada.pdf"

    def test_usa_timeout_maior_que_o_padrao(self):
        """A minuta levou 81s contra o sandbox; com os 30s do padrão ela
        estourava e virava "a seguradora não respondeu"."""
        from apps.emissoes.conectores.junto import TIMEOUT_MINUTA, TIMEOUT_PADRAO

        vistos = {}

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/authentication"):
                return TOKEN
            vistos["timeout"] = request.extensions.get("timeout", {}).get("read")
            return httpx.Response(
                200, json={"documentNumber": 5, "draftUrl": "u", "hasHangs": False}
            )

        con = ConectorJunto(SeguradoraFake(), transport=httpx.MockTransport(handler))
        con.gerar_minuta(
            external_id="5",
            edital="E",
            segurado=SeguradoJunto(insured_id=1, address_id=2),
        )

        assert TIMEOUT_MINUTA > TIMEOUT_PADRAO
        assert vistos["timeout"] == TIMEOUT_MINUTA

    def test_omite_endereco_quando_nao_ha(self):
        enviados = {}

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/authentication"):
                return TOKEN
            enviados["corpo"] = json.loads(request.content)
            return httpx.Response(
                200, json={"documentNumber": 3, "draftUrl": "u", "hasHangs": False}
            )

        con = ConectorJunto(SeguradoraFake(), transport=httpx.MockTransport(handler))
        con.gerar_minuta(
            external_id="3",
            edital="E",
            segurado=SeguradoJunto(insured_id=7, address_id=None),
        )

        assert enviados["corpo"]["insured"] == {"insuredId": 7}


# ─── Service ─────────────────────────────────────────────────────────────────

from django.core.exceptions import ValidationError  # noqa: E402

from apps.emissoes.conectores.base import Pendencia, RespostaMinuta  # noqa: E402
from apps.emissoes.models import EmissaoSeguradora  # noqa: E402
from apps.emissoes.services import emissao_cotar, emissao_gerar_minuta  # noqa: E402
from apps.segurados.models import Segurado  # noqa: E402

from .conftest import ConectorFake  # noqa: E402


class ConectorFakeMinuta(ConectorFake):
    """Estende o falso do passo 1 com o passo 2."""

    def __init__(self, *, segurado_existe=True, resposta_minuta=None):
        super().__init__()
        self.segurado_existe = segurado_existe
        self.cadastrou = None
        self.resposta_minuta = resposta_minuta or RespostaMinuta(
            document_number="6497972",
            url_minuta="",
            tem_pendencias=True,
            pendencias=[
                Pendencia(
                    codigo=12,
                    descricao="Fora dos parâmetros de crédito.",
                    departamento="Crédito - Crédito",
                    email="plataforma@juntoseguros.com",
                )
            ],
        )

    def buscar_segurado(self, *, federal_id):
        self.chamadas.append(("buscar_segurado", federal_id))
        return (
            SeguradoJunto(insured_id=1, address_id=2) if self.segurado_existe else None
        )

    def cadastrar_segurado(self, *, dados):
        self.cadastrou = dados
        return SeguradoJunto(insured_id=99, address_id=98)

    def gerar_minuta(self, *, external_id, edital, segurado, forcar_url=False):
        self.chamadas.append(("gerar_minuta", forcar_url))
        return self.resposta_minuta


@pytest.fixture
def cotacao_cotada(cotacao, seguradora):
    cotacao.segurado = Segurado.objects.create(
        cnpj="22.333.444/0001-66",
        nome="COMERCIO VERDE ALIMENTOS LTDA",
        endereco="RUA DAS FLORES 100",
        cidade="FORTALEZA",
        estado="CE",
        cep="60000-000",
        natureza_juridica="206-2 - Sociedade Empresária Limitada",
    )
    cotacao.edital = "EDITAL-42"
    cotacao.save()
    emissao_cotar(
        cotacao_id=cotacao.pk, seguradora_id=seguradora.pk, conector=ConectorFake()
    )
    return cotacao


@pytest.mark.django_db
class TestServiceMinuta:
    def test_grava_documento_etapa_e_pendencias(self, cotacao_cotada, seguradora):
        emissao = emissao_gerar_minuta(
            cotacao_id=cotacao_cotada.pk,
            seguradora_id=seguradora.pk,
            conector=ConectorFakeMinuta(),
        )

        assert emissao.etapa == EmissaoSeguradora.ETAPA_MINUTA
        assert emissao.document_number == "6497972"
        assert emissao.url_minuta == ""
        assert emissao.tem_pendencias is True
        assert emissao.pendencias[0]["codigo"] == 12
        assert emissao.pendencias[0]["departamento"] == "Crédito - Crédito"

    def test_nao_cria_emissao_nova(self, cotacao_cotada, seguradora):
        emissao_gerar_minuta(
            cotacao_id=cotacao_cotada.pk,
            seguradora_id=seguradora.pk,
            conector=ConectorFakeMinuta(),
        )

        assert EmissaoSeguradora.objects.filter(cotacao=cotacao_cotada).count() == 1

    def test_cadastra_o_segurado_quando_nao_existe_na_junto(
        self, cotacao_cotada, seguradora
    ):
        con = ConectorFakeMinuta(segurado_existe=False)

        emissao_gerar_minuta(
            cotacao_id=cotacao_cotada.pk, seguradora_id=seguradora.pk, conector=con
        )

        assert con.cadastrou is not None
        assert con.cadastrou.federal_id == "22333444000166"
        assert con.cadastrou.cidade == "FORTALEZA"
        # natureza jurídica 2xx = entidade empresarial = privada
        assert con.cadastrou.tipo == 9

    def test_nao_cadastra_quando_o_segurado_ja_existe(self, cotacao_cotada, seguradora):
        con = ConectorFakeMinuta(segurado_existe=True)

        emissao_gerar_minuta(
            cotacao_id=cotacao_cotada.pk, seguradora_id=seguradora.pk, conector=con
        )

        assert con.cadastrou is None

    def test_natureza_publica_vira_tipo_8(self, cotacao_cotada, seguradora):
        cotacao_cotada.segurado.natureza_juridica = (
            "103-1 - Órgão Público do Poder Executivo Federal"
        )
        cotacao_cotada.segurado.save()
        con = ConectorFakeMinuta(segurado_existe=False)

        emissao_gerar_minuta(
            cotacao_id=cotacao_cotada.pk, seguradora_id=seguradora.pk, conector=con
        )

        assert con.cadastrou.tipo == 8

    def test_repassa_forcar_url(self, cotacao_cotada, seguradora):
        con = ConectorFakeMinuta()

        emissao_gerar_minuta(
            cotacao_id=cotacao_cotada.pk,
            seguradora_id=seguradora.pk,
            forcar_url=True,
            conector=con,
        )

        assert ("gerar_minuta", True) in con.chamadas

    def test_recusa_sem_segurado(self, cotacao, seguradora):
        emissao_cotar(
            cotacao_id=cotacao.pk, seguradora_id=seguradora.pk, conector=ConectorFake()
        )
        cotacao.edital = "EDITAL-42"
        cotacao.save()

        with pytest.raises(ValidationError, match="segurado"):
            emissao_gerar_minuta(
                cotacao_id=cotacao.pk,
                seguradora_id=seguradora.pk,
                conector=ConectorFakeMinuta(),
            )

    def test_recusa_sem_edital(self, cotacao_cotada, seguradora):
        cotacao_cotada.edital = ""
        cotacao_cotada.save()

        with pytest.raises(ValidationError, match="edital"):
            emissao_gerar_minuta(
                cotacao_id=cotacao_cotada.pk,
                seguradora_id=seguradora.pk,
                conector=ConectorFakeMinuta(),
            )

    def test_recusa_quando_ainda_nao_cotou(self, cotacao, seguradora):
        with pytest.raises(ValidationError, match="cotar"):
            emissao_gerar_minuta(
                cotacao_id=cotacao.pk,
                seguradora_id=seguradora.pk,
                conector=ConectorFakeMinuta(),
            )

    def test_nao_chama_a_seguradora_quando_a_validacao_falha(self, cotacao, seguradora):
        con = ConectorFakeMinuta()

        with pytest.raises(ValidationError):
            emissao_gerar_minuta(
                cotacao_id=cotacao.pk, seguradora_id=seguradora.pk, conector=con
            )

        assert con.chamadas == []


# ─── API ─────────────────────────────────────────────────────────────────────

from django.contrib.auth import get_user_model  # noqa: E402
from django.urls import reverse  # noqa: E402
from rest_framework import status  # noqa: E402
from rest_framework.test import APIClient  # noqa: E402

User = get_user_model()


@pytest.fixture
def cliente_api(db):
    usuario = User.objects.create_user(email="op@cajuina.com.br", password="x")
    api = APIClient()
    api.force_authenticate(user=usuario)
    return api


@pytest.mark.django_db
class TestApiMinuta:
    def _post(self, cliente, cotacao, corpo):
        return cliente.post(
            reverse("cotacao-emissao-minuta", args=[cotacao.pk]), corpo, format="json"
        )

    def test_gera_e_devolve_as_pendencias(
        self, cliente_api, cotacao_cotada, seguradora, monkeypatch
    ):
        monkeypatch.setattr(
            "apps.emissoes.services.get_conector",
            lambda seguradora, **kw: ConectorFakeMinuta(),
        )

        resposta = self._post(
            cliente_api, cotacao_cotada, {"seguradora": seguradora.pk}
        )

        assert resposta.status_code == status.HTTP_200_OK
        dados = resposta.data["data"]
        assert dados["etapa"] == EmissaoSeguradora.ETAPA_MINUTA
        assert dados["document_number"] == "6497972"
        assert dados["tem_pendencias"] is True
        assert dados["pendencias"][0]["departamento"] == "Crédito - Crédito"

    def test_forcar_url_chega_ao_service(
        self, cliente_api, cotacao_cotada, seguradora, monkeypatch
    ):
        con = ConectorFakeMinuta(
            resposta_minuta=RespostaMinuta(
                document_number="6497972",
                url_minuta="https://junto/forcada.pdf",
                tem_pendencias=True,
                pendencias=[],
            )
        )
        monkeypatch.setattr(
            "apps.emissoes.services.get_conector", lambda seguradora, **kw: con
        )

        resposta = self._post(
            cliente_api,
            cotacao_cotada,
            {"seguradora": seguradora.pk, "forcar_url": True},
        )

        assert resposta.status_code == status.HTTP_200_OK
        assert resposta.data["data"]["url_minuta"] == "https://junto/forcada.pdf"
        assert ("gerar_minuta", True) in con.chamadas

    def test_sem_seguradora_no_body_e_400(self, cliente_api, cotacao_cotada):
        resposta = self._post(cliente_api, cotacao_cotada, {})

        assert resposta.status_code == status.HTTP_400_BAD_REQUEST
        assert "seguradora" in resposta.data["detail"].lower()

    def test_sem_cotar_antes_e_400(self, cliente_api, cotacao, seguradora):
        resposta = self._post(cliente_api, cotacao, {"seguradora": seguradora.pk})

        assert resposta.status_code == status.HTTP_400_BAD_REQUEST
        assert "cotar" in resposta.data["detail"]

    def test_cotacao_inexistente_e_404(self, cliente_api, db, seguradora):
        resposta = cliente_api.post(
            reverse("cotacao-emissao-minuta", args=[99999]),
            {"seguradora": seguradora.pk},
            format="json",
        )
        assert resposta.status_code == status.HTTP_404_NOT_FOUND

    def test_sem_token_e_401(self, cotacao_cotada, seguradora):
        resposta = APIClient().post(
            reverse("cotacao-emissao-minuta", args=[cotacao_cotada.pk]),
            {"seguradora": seguradora.pk},
            format="json",
        )
        assert resposta.status_code == status.HTTP_401_UNAUTHORIZED
