"""Testes do serviço com um conector falso.

O falso implementa a mesma interface do `ConectorJunto` — é o que garante que
`services.py` não sabe nada sobre a Junto. Cenário e conector falso vêm do
`conftest.py` do pacote.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.apolices.models import Apolice
from apps.cotacoes.models import Cotacao
from apps.emissoes.models import EmissaoSeguradora
from apps.emissoes.services import emissao_cotar
from apps.modalidades.models import ModalidadeSeguradora
from apps.seguradoras.models import Seguradora

from .conftest import ConectorFake


@pytest.mark.django_db
class TestEmissaoCotar:
    def test_cria_a_emissao_na_etapa_cotada(self, cotacao):
        conector = ConectorFake()
        emissao = emissao_cotar(
            cotacao_id=cotacao.pk,
            seguradora_id=cotacao.seguradora_id,
            conector=conector,
        )

        assert emissao.etapa == EmissaoSeguradora.ETAPA_COTADA
        assert emissao.external_id == "2601513"
        assert emissao.integracao == "junto"
        assert emissao.ambiente == "sandbox"
        assert emissao.premio_total == Decimal("500.00")
        assert emissao.taxa == Decimal("0.500000")
        assert emissao.comissao_percentual == Decimal("27.00")
        assert emissao.comissao_valor == Decimal("135.00")
        assert emissao.numero_parcelas == 1
        assert emissao.numero_max_parcelas == 3

    def test_grava_as_opcoes_de_parcelamento(self, cotacao):
        emissao = emissao_cotar(
            cotacao_id=cotacao.pk,
            seguradora_id=cotacao.seguradora_id,
            conector=ConectorFake(),
        )

        assert len(emissao.opcoes_parcelamento) == 1
        opcao = emissao.opcoes_parcelamento[0]
        assert opcao["numero_parcelas"] == 1
        assert opcao["parcelas"][0]["numero"] == 1

    def test_guarda_o_snapshot_do_que_foi_enviado(self, cotacao):
        emissao = emissao_cotar(
            cotacao_id=cotacao.pk,
            seguradora_id=cotacao.seguradora_id,
            conector=ConectorFake(),
        )

        assert emissao.dados_cotados == {
            "importancia_segurada": "100000.00",
            "prazo_dias": 365,
            "data_inicio": "2026-09-01",
            "modalidade_id": cotacao.modalidade_id,
            "tomador_cnpj": "02567157000129",
        }

    def test_guarda_payload_cru_para_auditoria(self, cotacao):
        emissao = emissao_cotar(
            cotacao_id=cotacao.pk,
            seguradora_id=cotacao.seguradora_id,
            conector=ConectorFake(),
        )
        assert emissao.ultimo_request == {"modalityId": 98}
        assert emissao.ultima_resposta == {"id": 2601513}

    def test_segunda_chamada_atualiza_em_vez_de_duplicar(self, cotacao):
        conector = ConectorFake()
        emissao_cotar(
            cotacao_id=cotacao.pk,
            seguradora_id=cotacao.seguradora_id,
            conector=conector,
        )
        emissao_cotar(
            cotacao_id=cotacao.pk,
            seguradora_id=cotacao.seguradora_id,
            conector=conector,
        )

        assert [c[0] for c in conector.chamadas] == ["cotar", "atualizar_cotacao"]
        assert EmissaoSeguradora.objects.count() == 1

    def test_passa_o_vencimento_do_par_tomador_seguradora(self, cotacao, seguradora):
        seguradora.vencimento_dias = 7
        seguradora.save()

        conector = ConectorFake()
        emissao_cotar(
            cotacao_id=cotacao.pk,
            seguradora_id=cotacao.seguradora_id,
            conector=conector,
        )

        dados = conector.chamadas[0][1]
        assert dados.vencimento_primeira_parcela == date.today() + timedelta(days=7)

    def test_cota_em_duas_seguradoras_na_mesma_cotacao(self, cotacao, seguradora):
        """Cotar na segunda não mexe na primeira: são linhas independentes."""
        outra = Seguradora.objects.create(
            nome="Pottencial Seguradora",
            premio_minimo="100.00",
            integracao=Seguradora.INTEGRACAO_JUNTO,
            api_ambiente=Seguradora.AMBIENTE_SANDBOX,
            api_client_id="cid",
            api_client_secret="segredo",
        )
        ModalidadeSeguradora.objects.create(
            modalidade=cotacao.modalidade, seguradora=outra, codigo_seguradora="98"
        )
        conector = ConectorFake()

        emissao_cotar(
            cotacao_id=cotacao.pk, seguradora_id=seguradora.pk, conector=conector
        )
        emissao_cotar(cotacao_id=cotacao.pk, seguradora_id=outra.pk, conector=conector)

        assert EmissaoSeguradora.objects.filter(cotacao=cotacao).count() == 2
        assert [c[0] for c in conector.chamadas] == ["cotar", "cotar"]

    def test_recotar_a_mesma_seguradora_nao_cria_linha_nova(self, cotacao, seguradora):
        conector = ConectorFake()

        emissao_cotar(
            cotacao_id=cotacao.pk, seguradora_id=seguradora.pk, conector=conector
        )
        emissao_cotar(
            cotacao_id=cotacao.pk, seguradora_id=seguradora.pk, conector=conector
        )

        assert EmissaoSeguradora.objects.filter(cotacao=cotacao).count() == 1
        assert [c[0] for c in conector.chamadas] == ["cotar", "atualizar_cotacao"]

    def test_cotar_nao_muda_a_seguradora_escolhida(self, cotacao, seguradora):
        """Cotar e escolher são ações separadas: a lupa não escolhe por você."""
        cotacao.seguradora = None
        cotacao.save()

        emissao_cotar(
            cotacao_id=cotacao.pk, seguradora_id=seguradora.pk, conector=ConectorFake()
        )

        cotacao.refresh_from_db()
        assert cotacao.seguradora_id is None


@pytest.mark.django_db
class TestValidacoes:
    def _erro(self, cotacao):
        with pytest.raises(ValidationError) as exc:
            emissao_cotar(
                cotacao_id=cotacao.pk,
                seguradora_id=cotacao.seguradora_id,
                conector=ConectorFake(),
            )
        return exc.value.messages[0]

    def test_recusa_cotacao_nao_aprovada(self, cotacao):
        cotacao.status = Cotacao.STATUS_INICIADO
        cotacao.save()
        assert "precisa estar aprovada" in self._erro(cotacao)

    def test_recusa_seguradora_sem_integracao(self, cotacao, seguradora):
        seguradora.integracao = ""
        seguradora.save()
        assert "emissão manual" in self._erro(cotacao)

    def test_recusa_seguradora_sem_credencial(self, cotacao, seguradora):
        seguradora.api_client_secret = ""
        seguradora.save()
        assert "Credenciais" in self._erro(cotacao)

    def test_recusa_modalidade_sem_mapeamento(self, cotacao, modalidade, seguradora):
        ModalidadeSeguradora.objects.filter(
            modalidade=modalidade, seguradora=seguradora
        ).delete()
        assert "não está mapeada" in self._erro(cotacao)

    def test_recusa_cotacao_que_ja_virou_apolice(self, cotacao, seguradora):
        Apolice.objects.create(
            cotacao=cotacao,
            seguradora=seguradora,
            numero_apolice="01-0001-0000001",
            valor_seguradora="500.00",
        )
        assert "já tem apólice" in self._erro(cotacao)

    def test_recusa_sem_importancia_segurada(self, cotacao):
        cotacao.importancia_segurada = None
        cotacao.save()
        assert "importância segurada" in self._erro(cotacao)

    def test_recusa_sem_prazo(self, cotacao):
        cotacao.prazo_dias = None
        cotacao.save()
        assert "prazo em dias" in self._erro(cotacao)

    def test_recusa_sem_data_inicio(self, cotacao):
        cotacao.data_inicio = None
        cotacao.save()
        assert "data de início" in self._erro(cotacao)

    def test_recusa_tomador_sem_cnpj(self, cotacao):
        cotacao.tomador.cnpj = ""
        cotacao.tomador.save()
        assert "CNPJ" in self._erro(cotacao)

    def test_nao_chama_a_seguradora_quando_a_validacao_falha(self, cotacao):
        cotacao.status = Cotacao.STATUS_INICIADO
        cotacao.save()
        conector = ConectorFake()
        with pytest.raises(ValidationError):
            emissao_cotar(
                cotacao_id=cotacao.pk,
                seguradora_id=cotacao.seguradora_id,
                conector=conector,
            )
        assert conector.chamadas == []


@pytest.mark.django_db
class TestAmbiente:
    def test_recomeca_quando_o_ambiente_muda_e_nada_foi_gerado(
        self, cotacao, seguradora
    ):
        """Só a cotação existe lá: descartar o id de sandbox é seguro."""
        conector = ConectorFake()
        emissao_cotar(
            cotacao_id=cotacao.pk,
            seguradora_id=cotacao.seguradora_id,
            conector=conector,
        )

        seguradora.api_ambiente = Seguradora.AMBIENTE_PRODUCAO
        seguradora.save()
        emissao = emissao_cotar(
            cotacao_id=cotacao.pk,
            seguradora_id=cotacao.seguradora_id,
            conector=conector,
        )

        assert [c[0] for c in conector.chamadas] == ["cotar", "cotar"]
        assert emissao.ambiente == "producao"

    def test_recusa_quando_o_ambiente_muda_depois_da_minuta(self, cotacao, seguradora):
        emissao = emissao_cotar(
            cotacao_id=cotacao.pk,
            seguradora_id=cotacao.seguradora_id,
            conector=ConectorFake(),
        )
        emissao.etapa = EmissaoSeguradora.ETAPA_MINUTA
        emissao.save()

        seguradora.api_ambiente = Seguradora.AMBIENTE_PRODUCAO
        seguradora.save()

        with pytest.raises(ValidationError, match="outro ambiente"):
            emissao_cotar(
                cotacao_id=cotacao.pk,
                seguradora_id=cotacao.seguradora_id,
                conector=ConectorFake(),
            )
