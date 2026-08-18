"""Cenário compartilhado pelos testes de service e de API."""

from datetime import date
from decimal import Decimal

import pytest

from apps.cotacoes.models import Cotacao
from apps.emissoes.conectores.base import (
    OpcaoParcelamento,
    Parcela,
    RespostaCotacao,
)
from apps.modalidades.models import Modalidade, ModalidadeSeguradora
from apps.seguradoras.models import Seguradora
from apps.tomadores.models import Tomador

RESPOSTA = RespostaCotacao(
    external_id="2601513",
    premio_liquido=Decimal("500.00"),
    premio_total=Decimal("500.00"),
    taxa=Decimal("0.5"),
    comissao_percentual=Decimal("27.0"),
    comissao_valor=Decimal("135.00"),
    numero_parcelas=1,
    numero_max_parcelas=3,
    opcoes_parcelamento=[
        OpcaoParcelamento(
            numero_parcelas=1,
            vencimento_primeira_parcela=date(2026, 8, 25),
            premio_total=Decimal("500.00"),
            parcelas=[
                Parcela(
                    numero=1,
                    vencimento=date(2026, 8, 25),
                    valor=Decimal("500.00"),
                    iof=Decimal("0.00"),
                    custo_apolice=Decimal("0.00"),
                    adicional_fracionamento=Decimal("0.00"),
                )
            ],
        )
    ],
    url_cotacao="https://sandbox.junto/quote/1",
    request_bruto={"modalityId": 98},
    resposta_bruta={"id": 2601513},
)


class ConectorFake:
    """Implementa a mesma interface do ConectorJunto, sem rede."""

    def __init__(self, resposta=RESPOSTA):
        self.chamadas = []
        self.resposta = resposta

    def cotar(self, *, dados):
        self.chamadas.append(("cotar", dados))
        return self.resposta

    def atualizar_cotacao(self, *, external_id, dados):
        self.chamadas.append(("atualizar_cotacao", dados))
        return self.resposta


@pytest.fixture
def seguradora(db):
    return Seguradora.objects.create(
        nome="Junto Seguros",
        premio_minimo="100.00",
        integracao=Seguradora.INTEGRACAO_JUNTO,
        api_ambiente=Seguradora.AMBIENTE_SANDBOX,
        api_client_id="cid",
        api_client_secret="segredo",
    )


@pytest.fixture
def modalidade(db, seguradora):
    modalidade = Modalidade.objects.create(nome="Executante Fornecedor")
    ModalidadeSeguradora.objects.create(
        modalidade=modalidade, seguradora=seguradora, codigo_seguradora="98"
    )
    return modalidade


@pytest.fixture
def cotacao(db, seguradora, modalidade):
    tomador = Tomador.objects.create(nome="Construtora Alfa", cnpj="02.567.157/0001-29")
    return Cotacao.objects.create(
        tomador=tomador,
        modalidade=modalidade,
        seguradora=seguradora,
        status=Cotacao.STATUS_APROVADO,
        importancia_segurada="100000.00",
        data_inicio=date(2026, 9, 1),
        prazo_dias=365,
    )
