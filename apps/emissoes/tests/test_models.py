"""A emissão é por par cotação × seguradora.

Cotar em três seguradoras e comparar antes de escolher é requisito; era o que
o legado fazia com uma linha por seguradora em `valores_simulacao`.
"""

import pytest
from django.db import IntegrityError, transaction

from apps.emissoes.models import EmissaoSeguradora
from apps.seguradoras.models import Seguradora


@pytest.mark.django_db
class TestEmissaoPorSeguradora:
    def test_permite_duas_seguradoras_na_mesma_cotacao(self, cotacao, seguradora):
        outra = Seguradora.objects.create(
            nome="Pottencial Seguradora", premio_minimo="100.00"
        )

        EmissaoSeguradora.objects.create(
            cotacao=cotacao,
            seguradora=seguradora,
            integracao="junto",
            ambiente="sandbox",
        )
        EmissaoSeguradora.objects.create(
            cotacao=cotacao, seguradora=outra, integracao="", ambiente="sandbox"
        )

        assert cotacao.emissoes.count() == 2

    def test_recusa_a_mesma_seguradora_duas_vezes(self, cotacao, seguradora):
        EmissaoSeguradora.objects.create(
            cotacao=cotacao,
            seguradora=seguradora,
            integracao="junto",
            ambiente="sandbox",
        )

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                EmissaoSeguradora.objects.create(
                    cotacao=cotacao,
                    seguradora=seguradora,
                    integracao="junto",
                    ambiente="sandbox",
                )
