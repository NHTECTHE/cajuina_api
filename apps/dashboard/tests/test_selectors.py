from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.apolices.models import Apolice
from apps.cotacoes.models import Cotacao
from apps.dashboard import selectors
from apps.modalidades.models import Modalidade
from apps.seguradoras.models import Seguradora
from apps.tomadores.models import Tomador

User = get_user_model()


class TestPeriodoRange:
    def test_dia_cobre_apenas_a_data_de_referencia(self):
        inicio, fim = selectors.periodo_range("dia", hoje=date(2026, 8, 5))

        assert inicio == date(2026, 8, 5)
        assert fim == date(2026, 8, 5)

    def test_mes_vai_do_primeiro_ao_ultimo_dia(self):
        inicio, fim = selectors.periodo_range("mes", hoje=date(2026, 8, 5))

        assert inicio == date(2026, 8, 1)
        assert fim == date(2026, 8, 31)

    def test_mes_de_fevereiro_em_ano_bissexto(self):
        inicio, fim = selectors.periodo_range("mes", hoje=date(2024, 2, 10))

        assert inicio == date(2024, 2, 1)
        assert fim == date(2024, 2, 29)

    def test_mes_de_dezembro_nao_estoura_o_ano(self):
        inicio, fim = selectors.periodo_range("mes", hoje=date(2026, 12, 15))

        assert inicio == date(2026, 12, 1)
        assert fim == date(2026, 12, 31)

    def test_ano_cobre_o_ano_inteiro(self):
        inicio, fim = selectors.periodo_range("ano", hoje=date(2026, 8, 5))

        assert inicio == date(2026, 1, 1)
        assert fim == date(2026, 12, 31)

    def test_periodo_invalido_cai_para_mes(self):
        inicio, fim = selectors.periodo_range("semana", hoje=date(2026, 8, 5))

        assert (inicio, fim) == (date(2026, 8, 1), date(2026, 8, 31))

    def test_rotulo_por_periodo(self):
        assert selectors.periodo_rotulo("dia", date(2026, 8, 5)) == "05/08/2026"
        assert selectors.periodo_rotulo("mes", date(2026, 8, 5)) == "08/2026"
        assert selectors.periodo_rotulo("ano", date(2026, 8, 5)) == "2026"


@pytest.fixture
def cenario(db):
    """Uma seguradora, uma modalidade, dois tomadores e três cotações."""
    seguradora = Seguradora.objects.create(
        nome="AVLA", premio_minimo=Decimal("100.00"), taxa_comissao=Decimal("10.00"),
        meta=Decimal("10000.00"),
    )
    modalidade = Modalidade.objects.create(nome="Garantia")
    tomador = Tomador.objects.create(cnpj="11.111.111/0001-11", nome="ACME")

    iniciada = Cotacao.objects.create(
        status=Cotacao.STATUS_INICIADO, tomador=tomador, modalidade=modalidade,
        seguradora=seguradora, premio=Decimal("500.00"),
    )
    aprovada = Cotacao.objects.create(
        status=Cotacao.STATUS_APROVADO, tomador=tomador, modalidade=modalidade,
        seguradora=seguradora, premio=Decimal("300.00"),
    )
    emitida = Cotacao.objects.create(
        status=Cotacao.STATUS_EMITIDO, tomador=tomador, modalidade=modalidade,
        seguradora=seguradora, premio=Decimal("1000.00"),
    )
    apolice = Apolice.objects.create(
        cotacao=emitida, seguradora=seguradora, numero_apolice="AP-1",
        valor_seguradora=Decimal("900.00"),
    )

    return {
        "seguradora": seguradora,
        "modalidade": modalidade,
        "tomador": tomador,
        "iniciada": iniciada,
        "aprovada": aprovada,
        "emitida": emitida,
        "apolice": apolice,
    }


@pytest.mark.django_db
class TestResumo:
    def test_producao_soma_premio_das_apolices_do_periodo(self, cenario):
        resultado = selectors.resumo(periodo="mes")

        assert resultado["producao"] == Decimal("1000.00")

    def test_conta_apolices_do_periodo(self, cenario):
        resultado = selectors.resumo(periodo="mes")

        assert resultado["apolices"] == 1

    def test_tomadores_no_periodo_e_total(self, cenario):
        Tomador.objects.create(cnpj="22.222.222/0001-22", nome="OUTRA")

        resultado = selectors.resumo(periodo="mes")

        assert resultado["tomadores"] == {"periodo": 2, "total": 2}

    def test_cotacoes_por_status(self, cenario):
        resultado = selectors.resumo(periodo="mes")

        assert resultado["cotacoes"] == {"iniciadas": 1, "aprovadas": 1, "emitidas": 1}

    def test_inclui_metadados_do_periodo(self, cenario):
        resultado = selectors.resumo(periodo="ano")

        assert resultado["periodo"]["tipo"] == "ano"
        assert resultado["periodo"]["rotulo"] == str(timezone.localdate().year)

    def test_base_vazia_devolve_zeros(self, db):
        resultado = selectors.resumo(periodo="mes")

        assert resultado["producao"] == Decimal("0.00")
        assert resultado["apolices"] == 0
        assert resultado["tomadores"] == {"periodo": 0, "total": 0}
        assert resultado["cotacoes"] == {"iniciadas": 0, "aprovadas": 0, "emitidas": 0}

    def test_apolice_com_premio_nulo_nao_quebra(self, cenario):
        cenario["emitida"].premio = None
        cenario["emitida"].save()

        resultado = selectors.resumo(periodo="mes")

        assert resultado["producao"] == Decimal("0.00")


@pytest.mark.django_db
class TestComissoes:
    def _apolice(self, cenario, premio, status_comissao, numero):
        cotacao = Cotacao.objects.create(
            status=Cotacao.STATUS_EMITIDO,
            tomador=cenario["tomador"],
            modalidade=cenario["modalidade"],
            seguradora=cenario["seguradora"],
            premio=Decimal(premio),
        )
        return Apolice.objects.create(
            cotacao=cotacao,
            seguradora=cenario["seguradora"],
            numero_apolice=numero,
            valor_seguradora=Decimal(premio),
            status_pagamento_comissao=status_comissao,
        )

    def test_agrupa_por_status_de_comissao(self, cenario):
        # taxa_comissao da seguradora do cenário é 10%
        self._apolice(cenario, "1000.00", "A Receber", "AP-2")
        self._apolice(cenario, "2000.00", "Recebido", "AP-3")
        self._apolice(cenario, "500.00", "Atrasado", "AP-4")

        resultado = selectors.comissoes()

        # A apólice do fixture (premio 1000, status default "A Receber") entra em a_receber
        assert resultado["a_receber"] == Decimal("200.00")
        assert resultado["pago"] == Decimal("200.00")
        assert resultado["em_atraso"] == Decimal("50.00")

    def test_a_pagar_soma_a_receber_com_em_atraso(self, cenario):
        self._apolice(cenario, "500.00", "Atrasado", "AP-4")

        resultado = selectors.comissoes()

        assert resultado["a_pagar"] == resultado["a_receber"] + resultado["em_atraso"]

    def test_seguradora_sem_taxa_de_comissao_conta_zero(self, cenario):
        cenario["seguradora"].taxa_comissao = None
        cenario["seguradora"].save()

        resultado = selectors.comissoes()

        assert resultado["a_receber"] == Decimal("0.00")

    def test_cotacao_com_premio_nulo_conta_zero(self, cenario):
        cenario["emitida"].premio = None
        cenario["emitida"].save()

        resultado = selectors.comissoes()

        assert resultado["a_receber"] == Decimal("0.00")

    def test_base_vazia_devolve_zeros(self, db):
        resultado = selectors.comissoes()

        assert resultado == {
            "a_receber": Decimal("0.00"),
            "pago": Decimal("0.00"),
            "em_atraso": Decimal("0.00"),
            "a_pagar": Decimal("0.00"),
        }


@pytest.mark.django_db
class TestPremioPorSeguradora:
    def test_devolve_valor_atual_meta_e_falta(self, cenario):
        ano = timezone.localdate().year

        resultado = selectors.premio_por_seguradora(ano=ano)

        assert len(resultado) == 1
        linha = resultado[0]
        assert linha["seguradora"] == "AVLA"
        assert linha["valor_atual"] == Decimal("1000.00")
        assert linha["meta"] == Decimal("10000.00")
        assert linha["falta"] == Decimal("9000.00")

    def test_falta_nunca_e_negativa(self, cenario):
        cenario["seguradora"].meta = Decimal("500.00")
        cenario["seguradora"].save()
        ano = timezone.localdate().year

        resultado = selectors.premio_por_seguradora(ano=ano)

        assert resultado[0]["falta"] == Decimal("0.00")

    def test_seguradora_sem_meta_devolve_meta_e_falta_nulas(self, cenario):
        cenario["seguradora"].meta = None
        cenario["seguradora"].save()
        ano = timezone.localdate().year

        resultado = selectors.premio_por_seguradora(ano=ano)

        assert resultado[0]["meta"] is None
        assert resultado[0]["falta"] is None

    def test_ignora_seguradora_inativa(self, cenario):
        cenario["seguradora"].ativo = False
        cenario["seguradora"].save()
        ano = timezone.localdate().year

        resultado = selectors.premio_por_seguradora(ano=ano)

        assert resultado == []

    def test_seguradora_ativa_sem_apolice_aparece_com_zero(self, cenario):
        Seguradora.objects.create(nome="ESSOR", premio_minimo=Decimal("100.00"))
        ano = timezone.localdate().year

        resultado = selectors.premio_por_seguradora(ano=ano)

        essor = next(linha for linha in resultado if linha["seguradora"] == "ESSOR")
        assert essor["valor_atual"] == Decimal("0.00")

    def test_ordena_por_valor_atual_decrescente(self, cenario):
        outra = Seguradora.objects.create(
            nome="ZURICH", premio_minimo=Decimal("100.00"), meta=Decimal("1000.00")
        )
        cotacao = Cotacao.objects.create(
            status=Cotacao.STATUS_EMITIDO, tomador=cenario["tomador"],
            modalidade=cenario["modalidade"], seguradora=outra, premio=Decimal("5000.00"),
        )
        Apolice.objects.create(
            cotacao=cotacao, seguradora=outra, numero_apolice="AP-Z",
            valor_seguradora=Decimal("5000.00"),
        )
        ano = timezone.localdate().year

        resultado = selectors.premio_por_seguradora(ano=ano)

        assert [linha["seguradora"] for linha in resultado] == ["ZURICH", "AVLA"]

    def test_ano_diferente_devolve_zero(self, cenario):
        resultado = selectors.premio_por_seguradora(ano=1999)

        assert resultado[0]["valor_atual"] == Decimal("0.00")


@pytest.mark.django_db
class TestNovosCadastros:
    @pytest.fixture
    def tomadores(self, db):
        user = User.objects.create_user(
            email="ana@empresa.com", password="x", first_name="Ana"
        )
        for i in range(1, 16):
            Tomador.objects.create(
                cnpj=f"{i:02d}.000.000/0001-00",
                nome=f"EMPRESA {i:02d}",
                contato=f"Contato {i:02d}",
                email=f"empresa{i:02d}@teste.com",
                telefone="(85) 99999-0000",
                criado_por=user if i % 2 == 0 else None,
            )
        return user

    def test_pagina_e_conta(self, tomadores):
        resultado = selectors.novos_cadastros(search="", page=1, page_size=10)

        assert len(resultado["results"]) == 10
        assert resultado["count"] == 15
        assert resultado["page"] == 1
        assert resultado["page_size"] == 10

    def test_segunda_pagina_traz_o_resto(self, tomadores):
        resultado = selectors.novos_cadastros(search="", page=2, page_size=10)

        assert len(resultado["results"]) == 5

    def test_pagina_fora_do_intervalo_devolve_vazio(self, tomadores):
        resultado = selectors.novos_cadastros(search="", page=99, page_size=10)

        assert resultado["results"] == []
        assert resultado["count"] == 15

    def test_ordena_do_mais_recente_para_o_mais_antigo(self, tomadores):
        resultado = selectors.novos_cadastros(search="", page=1, page_size=10)

        assert resultado["results"][0]["nome"] == "EMPRESA 15"

    def test_busca_por_nome(self, tomadores):
        resultado = selectors.novos_cadastros(search="EMPRESA 03", page=1, page_size=10)

        assert resultado["count"] == 1
        assert resultado["results"][0]["nome"] == "EMPRESA 03"

    def test_busca_por_email(self, tomadores):
        resultado = selectors.novos_cadastros(search="empresa07@", page=1, page_size=10)

        assert resultado["count"] == 1

    def test_busca_por_contato(self, tomadores):
        resultado = selectors.novos_cadastros(search="Contato 09", page=1, page_size=10)

        assert resultado["count"] == 1

    def test_criado_por_nulo_vira_none(self, tomadores):
        resultado = selectors.novos_cadastros(search="EMPRESA 01", page=1, page_size=10)

        assert resultado["results"][0]["criado_por"] is None

    def test_criado_por_usa_first_name(self, tomadores):
        resultado = selectors.novos_cadastros(search="EMPRESA 02", page=1, page_size=10)

        assert resultado["results"][0]["criado_por"] == "Ana"

    def test_base_vazia(self, db):
        resultado = selectors.novos_cadastros(search="", page=1, page_size=10)

        assert resultado == {"results": [], "count": 0, "page": 1, "page_size": 10}

    def test_page_size_tem_teto(self, tomadores):
        resultado = selectors.novos_cadastros(search="", page=1, page_size=9999)

        assert resultado["page_size"] == 100
