"""Leitura das emissões — o vocabulário que o e-mail, o serializer e a API usam."""

from decimal import Decimal

import pytest

from apps.emissoes.selectors import (
    emissoes_listar_por_cotacao,
    premios_cotados_por_seguradora,
)
from apps.emissoes.services import emissao_cotar

from .conftest import ConectorFake


@pytest.mark.django_db
class TestSelectors:
    def test_lista_vazia_quando_nunca_cotou(self, cotacao):
        assert list(emissoes_listar_por_cotacao(cotacao_id=cotacao.pk)) == []

    def test_lista_a_emissao_depois_de_cotar(self, cotacao, seguradora):
        emissao_cotar(
            cotacao_id=cotacao.pk, seguradora_id=seguradora.pk, conector=ConectorFake()
        )

        emissoes = list(emissoes_listar_por_cotacao(cotacao_id=cotacao.pk))

        assert len(emissoes) == 1
        assert emissoes[0].seguradora_id == seguradora.pk
        assert emissoes[0].external_id == "2601513"

    def test_mapa_de_premios_cotados(self, cotacao, seguradora):
        emissao_cotar(
            cotacao_id=cotacao.pk, seguradora_id=seguradora.pk, conector=ConectorFake()
        )

        assert premios_cotados_por_seguradora(cotacao_id=cotacao.pk) == {
            seguradora.pk: Decimal("500.00")
        }
