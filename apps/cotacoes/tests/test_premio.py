from decimal import Decimal

import pytest

from apps.cotacoes.models import Cotacao
from apps.cotacoes.services import cotacao_calcular_premio
from apps.modalidades.models import Modalidade
from apps.seguradoras.models import Seguradora
from apps.tomadores.models import Tomador, TomadorSeguradora


@pytest.fixture
def modalidade(db):
    return Modalidade.objects.create(nome="Garantia")


@pytest.fixture
def tomador(db):
    return Tomador.objects.create(nome="Tomador Teste", cnpj="11.222.333/0001-44")


@pytest.fixture
def seguradora(db):
    return Seguradora.objects.create(nome="Seg Teste", premio_minimo="150.00")


@pytest.mark.django_db
class TestCotacaoCalcularPremio:
    def test_abaixo_do_minimo_usa_o_minimo(self, tomador, modalidade, seguradora):
        """IS 10.000, taxa 2,5%, 30 dias -> 20,55 calculado, mas mínimo é 150."""
        TomadorSeguradora.objects.create(
            tomador=tomador, seguradora=seguradora, taxa="2.50"
        )
        cotacao = Cotacao.objects.create(
            tomador=tomador,
            modalidade=modalidade,
            seguradora=seguradora,
            importancia_segurada="10000.00",
            prazo_dias=30,
        )
        assert cotacao_calcular_premio(cotacao=cotacao) == Decimal("150.00")

    def test_acima_do_minimo_usa_o_calculado(self, tomador, modalidade, seguradora):
        """IS 1.000.000, taxa 5%, 365 dias -> 50.000,00."""
        TomadorSeguradora.objects.create(
            tomador=tomador, seguradora=seguradora, taxa="5.00"
        )
        cotacao = Cotacao.objects.create(
            tomador=tomador,
            modalidade=modalidade,
            seguradora=seguradora,
            importancia_segurada="1000000.00",
            prazo_dias=365,
        )
        assert cotacao_calcular_premio(cotacao=cotacao) == Decimal("50000.00")

    def test_usa_premio_minimo_do_par_quando_definido(
        self, tomador, modalidade, seguradora
    ):
        """Mínimo do par (500) tem precedência sobre o da seguradora (150)."""
        TomadorSeguradora.objects.create(
            tomador=tomador, seguradora=seguradora, taxa="2.50", premio_minimo="500.00"
        )
        cotacao = Cotacao.objects.create(
            tomador=tomador,
            modalidade=modalidade,
            seguradora=seguradora,
            importancia_segurada="10000.00",
            prazo_dias=30,
        )
        assert cotacao_calcular_premio(cotacao=cotacao) == Decimal("500.00")

    def test_sem_seguradora_retorna_none(self, tomador, modalidade):
        cotacao = Cotacao.objects.create(
            tomador=tomador,
            modalidade=modalidade,
            importancia_segurada="10000.00",
            prazo_dias=30,
        )
        assert cotacao_calcular_premio(cotacao=cotacao) is None

    def test_sem_vinculo_usa_premio_minimo_da_seguradora(
        self, tomador, modalidade, seguradora
    ):
        """Sem TomadorSeguradora não há taxa: cai no mínimo da seguradora."""
        cotacao = Cotacao.objects.create(
            tomador=tomador,
            modalidade=modalidade,
            seguradora=seguradora,
            importancia_segurada="10000.00",
            prazo_dias=30,
        )
        assert cotacao_calcular_premio(cotacao=cotacao) == Decimal("150.00")

    def test_sem_dados_de_calculo_retorna_none(self, tomador, modalidade, seguradora):
        """Sem IS nem prazo não há o que calcular."""
        TomadorSeguradora.objects.create(
            tomador=tomador, seguradora=seguradora, taxa="2.50"
        )
        cotacao = Cotacao.objects.create(
            tomador=tomador, modalidade=modalidade, seguradora=seguradora
        )
        assert cotacao_calcular_premio(cotacao=cotacao) is None
