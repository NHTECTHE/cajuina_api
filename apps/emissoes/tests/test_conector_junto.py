"""Testes do conector, sem rede.

A fixture `traditional_create.json` é a resposta real do sandbox da Junto,
gravada em 2026-08-18 — não um exemplo inventado a partir do swagger.
"""

import json
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from apps.emissoes.conectores.base import (
    DadosCotacao,
    ErroValidacaoSeguradora,
    SeguradoraIndisponivel,
)
from apps.emissoes.conectores.junto import ConectorJunto, limpar_cache_token

FIXTURES = Path(__file__).parent / "fixtures"
RESPOSTA_COTACAO = json.loads((FIXTURES / "traditional_create.json").read_text())


class SeguradoraFake:
    """O conector só precisa de pk, credenciais e ambiente — não do model."""

    def __init__(self, *, pk=1, ambiente="sandbox", client_id="cid", secret="segredo"):
        self.pk = pk
        self.api_ambiente = ambiente
        self.api_client_id = client_id
        self.api_client_secret = secret


DADOS = DadosCotacao(
    modalidade_codigo="98",
    tomador_cnpj="02.567.157/0001-29",
    importancia_segurada=Decimal("100000.00"),
    data_inicio=date(2026, 9, 1),
    prazo_dias=365,
    vencimento_primeira_parcela=date(2026, 8, 25),
)


@pytest.fixture(autouse=True)
def _cache_limpo():
    limpar_cache_token()
    yield
    limpar_cache_token()


def conector(handler, **kwargs):
    return ConectorJunto(
        SeguradoraFake(**kwargs), transport=httpx.MockTransport(handler)
    )


def resposta_auth(token="tok-123", expires=1800):
    return httpx.Response(
        200, json={"accessToken": token, "expiresIn": expires, "tokenType": "Bearer"}
    )


class TestAutenticacao:
    def test_token_e_reaproveitado_entre_chamadas(self):
        chamadas = []

        def handler(request):
            chamadas.append(str(request.url))
            if request.url.path.endswith("/authentication"):
                return resposta_auth()
            return httpx.Response(200, json=RESPOSTA_COTACAO)

        c = conector(handler)
        c.cotar(dados=DADOS)
        c.cotar(dados=DADOS)

        autenticacoes = [u for u in chamadas if u.endswith("/authentication")]
        assert len(autenticacoes) == 1, "o token deveria ter vindo do cache"

    def test_401_renova_o_token_uma_vez_e_repete(self):
        eventos = []

        def handler(request):
            if request.url.path.endswith("/authentication"):
                eventos.append("auth")
                return resposta_auth(token=f"tok-{eventos.count('auth')}")
            eventos.append("negocio")
            if eventos.count("negocio") == 1:
                return httpx.Response(401, json="Unauthorized")
            return httpx.Response(200, json=RESPOSTA_COTACAO)

        resposta = conector(handler).cotar(dados=DADOS)

        assert eventos == ["auth", "negocio", "auth", "negocio"]
        assert resposta.external_id == "2601513"

    def test_401_persistente_vira_indisponivel(self):
        def handler(request):
            if request.url.path.endswith("/authentication"):
                return resposta_auth()
            return httpx.Response(401, json="Unauthorized")

        with pytest.raises(SeguradoraIndisponivel):
            conector(handler).cotar(dados=DADOS)

    def test_credencial_em_branco_nao_chega_a_chamar_a_seguradora(self):
        def handler(request):
            raise AssertionError("não deveria ter saído requisição")

        with pytest.raises(ErroValidacaoSeguradora, match="não configuradas"):
            conector(handler, secret="").cotar(dados=DADOS)

    def test_credencial_recusada_e_erro_de_validacao(self):
        def handler(request):
            return httpx.Response(
                400, json=[{"message": "Credenciais inválidas.", "errorCode": 1001}]
            )

        with pytest.raises(ErroValidacaoSeguradora, match="Credenciais inválidas"):
            conector(handler).cotar(dados=DADOS)

    def test_ambiente_define_a_base_url(self):
        def handler(request):
            return resposta_auth()

        assert "box" in conector(handler).base_url
        assert "box" not in conector(handler, ambiente="producao").base_url


class TestPayload:
    def _capturar(self, **kwargs):
        capturado = {}

        def handler(request):
            if request.url.path.endswith("/authentication"):
                return resposta_auth()
            capturado["corpo"] = json.loads(request.content)
            capturado["metodo"] = request.method
            capturado["url"] = str(request.url)
            return httpx.Response(200, json=RESPOSTA_COTACAO)

        return handler, capturado

    def test_traduz_nosso_vocabulario_para_o_da_junto(self):
        handler, capturado = self._capturar()
        conector(handler).cotar(dados=DADOS)

        corpo = capturado["corpo"]
        assert corpo["modalityId"] == 98
        assert corpo["insuredAmount"] == 100000.00
        assert corpo["durationStart"] == "2026-09-01T00:00:00"
        assert corpo["durationDays"] == 365
        assert corpo["dueDateFirstInstallment"] == "2026-08-25T00:00:00"
        assert corpo["additionGuarantee"] == {
            "isAdditionalLabor": False,
            "isAggravateCoverage50": False,
        }
        assert capturado["metodo"] == "POST"

    def test_cnpj_vai_so_com_digitos(self):
        handler, capturado = self._capturar()
        conector(handler).cotar(dados=DADOS)
        assert capturado["corpo"]["policyholderFederalId"] == "02567157000129"

    def test_atualizar_usa_put_no_id_existente(self):
        handler, capturado = self._capturar()
        conector(handler).atualizar_cotacao(external_id="2601513", dados=DADOS)

        assert capturado["metodo"] == "PUT"
        assert capturado["url"].endswith("/guarantee/api/v2/traditional/2601513")

    def test_modalidade_nao_numerica_e_recusada_antes_da_rede(self):
        def handler(request):
            raise AssertionError("não deveria ter saído requisição")

        dados = replace(DADOS, modalidade_codigo="LICITANTE")
        with pytest.raises(ErroValidacaoSeguradora, match="numérico"):
            conector(handler).cotar(dados=dados)


class TestParsingDaResposta:
    def _cotar(self, corpo):
        def handler(request):
            if request.url.path.endswith("/authentication"):
                return resposta_auth()
            return httpx.Response(200, json=corpo)

        return conector(handler).cotar(dados=DADOS)

    def test_traduz_a_resposta_para_as_nossas_dataclasses(self):
        r = self._cotar(RESPOSTA_COTACAO)

        assert r.external_id == "2601513"
        assert r.premio_liquido == Decimal("500.00")
        assert r.premio_total == Decimal("500.00")
        assert r.taxa == Decimal("0.5")
        assert r.comissao_percentual == Decimal("27.0")
        assert r.comissao_valor == Decimal("135.00")
        assert r.numero_parcelas == 1
        assert r.numero_max_parcelas == 1
        assert r.url_cotacao.endswith("/3663633")

        assert len(r.opcoes_parcelamento) == 1
        opcao = r.opcoes_parcelamento[0]
        assert opcao.numero_parcelas == 1
        assert opcao.premio_total == Decimal("500.00")
        assert opcao.vencimento_primeira_parcela == date(2026, 8, 25)

        parcela = opcao.parcelas[0]
        assert parcela.numero == 1
        assert parcela.vencimento == date(2026, 8, 25)
        assert parcela.valor == Decimal("500.00")

    def test_dinheiro_vira_decimal_exato(self):
        """12.10 não pode virar 12.099999999999999644728632119949907.

        O corpo vai como texto cru de propósito: montar o dict em Python e
        deixar o json.dumps do teste serializar já normalizaria o número, e o
        teste passaria sem provar nada sobre o que chega pelo fio.
        """
        texto = json.dumps(RESPOSTA_COTACAO).replace(
            '"netPremiumValue": 500.0', '"netPremiumValue": 12.10'
        )
        assert '"netPremiumValue": 12.10' in texto

        def handler(request):
            if request.url.path.endswith("/authentication"):
                return resposta_auth()
            return httpx.Response(
                200, text=texto, headers={"Content-Type": "application/json"}
            )

        r = conector(handler).cotar(dados=DADOS)

        assert r.premio_liquido == Decimal("12.10")
        assert str(r.premio_liquido) == "12.10"
        assert r.premio_liquido != Decimal(12.10)

    def test_campo_novo_desconhecido_nao_quebra_o_parsing(self):
        corpo = {
            **RESPOSTA_COTACAO,
            "campoQueAJuntoInventouDepois": {"algo": [1, 2, 3]},
        }
        assert self._cotar(corpo).external_id == "2601513"

    def test_resposta_sem_id_e_tratada_como_indisponivel(self):
        corpo = {**RESPOSTA_COTACAO}
        corpo.pop("id")
        with pytest.raises(SeguradoraIndisponivel, match="identificador"):
            self._cotar(corpo)

    def test_put_sem_corpo_mantem_o_id_que_ja_tinhamos(self):
        def handler(request):
            if request.url.path.endswith("/authentication"):
                return resposta_auth()
            return httpx.Response(200, text="")

        r = conector(handler).atualizar_cotacao(external_id="2601513", dados=DADOS)
        assert r.external_id == "2601513"

    def test_guarda_request_e_resposta_crus_para_auditoria(self):
        r = self._cotar(RESPOSTA_COTACAO)
        assert r.request_bruto["modalityId"] == 98
        assert r.resposta_bruta["id"] == 2601513


class TestMapeamentoDeErro:
    def _erro(self, resposta):
        def handler(request):
            if request.url.path.endswith("/authentication"):
                return resposta_auth()
            if callable(resposta):
                return resposta(request)
            return resposta

        return conector(handler)

    def test_400_repassa_a_mensagem_da_junto(self):
        c = self._erro(
            httpx.Response(
                400,
                json=[
                    {
                        "message": "Corretor não possui permissão para visualizar o Tomador.",
                        "errorCode": 3002,
                    }
                ],
            )
        )
        with pytest.raises(ErroValidacaoSeguradora, match="não possui permissão"):
            c.cotar(dados=DADOS)

    def test_400_com_varias_notificacoes_junta_as_mensagens(self):
        c = self._erro(
            httpx.Response(
                400,
                json=[
                    {"message": "Limite insuficiente.", "errorCode": 1},
                    {"message": "Modalidade bloqueada.", "errorCode": 2},
                ],
            )
        )
        with pytest.raises(ErroValidacaoSeguradora) as exc:
            c.cotar(dados=DADOS)
        assert "Limite insuficiente." in str(exc.value)
        assert "Modalidade bloqueada." in str(exc.value)

    def test_500_vira_indisponivel(self):
        c = self._erro(httpx.Response(500, text="Internal Server Error"))
        with pytest.raises(SeguradoraIndisponivel):
            c.cotar(dados=DADOS)

    def test_timeout_vira_indisponivel(self):
        def estoura(request):
            if request.url.path.endswith("/authentication"):
                return resposta_auth()
            raise httpx.ReadTimeout("timeout", request=request)

        with pytest.raises(SeguradoraIndisponivel):
            conector(estoura).cotar(dados=DADOS)

    def test_erro_de_rede_vira_indisponivel(self):
        def cai(request):
            raise httpx.ConnectError("sem rota", request=request)

        with pytest.raises(SeguradoraIndisponivel):
            conector(cai).cotar(dados=DADOS)
