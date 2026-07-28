import datetime

import pytest

from apps.apolices.services import apolice_emitir
from apps.cotacoes.models import Cotacao
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
    return Seguradora.objects.create(
        nome="Seguradora Teste",
        premio_minimo="500.00",
        vencimento_dias=30,
    )


@pytest.fixture
def cotacao_aprovada(db, tomador, modalidade):
    return Cotacao.objects.create(
        tomador=tomador,
        modalidade=modalidade,
        status=Cotacao.STATUS_APROVADO,
    )


@pytest.mark.django_db
class TestApoliceEmitirVencimentoBoleto:
    def test_usa_vencimento_dias_da_seguradora_quando_sem_vinculo(
        self, cotacao_aprovada, seguradora
    ):
        apolice = apolice_emitir(
            cotacao=cotacao_aprovada,
            data={
                "seguradora": seguradora,
                "numero_apolice": "123",
                "valor_seguradora": "500.00",
            },
        )
        esperado = datetime.date.today() + datetime.timedelta(days=30)
        assert apolice.vencimento_boleto == esperado

    def test_usa_dias_vencimento_do_par_quando_definido(
        self, cotacao_aprovada, seguradora, tomador
    ):
        TomadorSeguradora.objects.create(
            tomador=tomador, seguradora=seguradora, taxa="1.50", dias_vencimento=45
        )
        apolice = apolice_emitir(
            cotacao=cotacao_aprovada,
            data={
                "seguradora": seguradora,
                "numero_apolice": "123",
                "valor_seguradora": "500.00",
            },
        )
        esperado = datetime.date.today() + datetime.timedelta(days=45)
        assert apolice.vencimento_boleto == esperado

    def test_payload_explicito_nao_e_recalculado(self, cotacao_aprovada, seguradora):
        data_manual = datetime.date(2026, 12, 25)
        apolice = apolice_emitir(
            cotacao=cotacao_aprovada,
            data={
                "seguradora": seguradora,
                "numero_apolice": "123",
                "valor_seguradora": "500.00",
                "vencimento_boleto": data_manual,
            },
        )
        assert apolice.vencimento_boleto == data_manual

    def test_sem_vinculo_e_sem_vencimento_na_seguradora_fica_none(
        self, cotacao_aprovada, tomador
    ):
        seguradora_sem_vencimento = Seguradora.objects.create(
            nome="Sem Vencimento", premio_minimo="500.00"
        )
        apolice = apolice_emitir(
            cotacao=cotacao_aprovada,
            data={
                "seguradora": seguradora_sem_vencimento,
                "numero_apolice": "123",
                "valor_seguradora": "500.00",
            },
        )
        assert apolice.vencimento_boleto is None
