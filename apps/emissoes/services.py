"""Orquestração da emissão integrada.

Este módulo não conhece a Junto: fala com `ConectorSeguradora` e com os nossos
models. Trocar de seguradora é trocar o conector que o registry devolve.
"""

from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.apolices.models import Apolice
from apps.apolices.services import vencimento_boleto_default
from apps.cotacoes.models import Cotacao
from apps.modalidades.models import ModalidadeNaoMapeada
from apps.modalidades.selectors import codigo_para_seguradora
from apps.seguradoras.models import Seguradora

from .conectores.base import DadosCotacao, IntegracaoNaoSuportada
from .conectores.junto import so_digitos
from .conectores.registry import get_conector
from .models import EmissaoSeguradora


def _quantizar(valor, casas: int):
    if valor is None:
        return None
    passo = Decimal(1).scaleb(-casas)
    return Decimal(valor).quantize(passo, rounding=ROUND_HALF_UP)


def _opcoes_para_json(opcoes) -> list[dict]:
    """Converte as opções para tipos que sobrevivem ao JSONField.

    Explícito em vez de `asdict` + encoder: o que é gravado tem de ser
    byte a byte o que a API devolve. Deixando o `DjangoJSONEncoder` converter na
    gravação, o POST devolveria o objeto em memória (Decimal virando número pelo
    renderer do DRF) e o GET devolveria o do banco (Decimal virando string),
    para o mesmo campo. Dinheiro sai como string, igual ao resto da API — é o
    que os DecimalField do DRF já fazem.
    """
    return [
        {
            "numero_parcelas": opcao.numero_parcelas,
            "vencimento_primeira_parcela": (
                opcao.vencimento_primeira_parcela.isoformat()
                if opcao.vencimento_primeira_parcela
                else None
            ),
            "premio_total": str(opcao.premio_total),
            "parcelas": [
                {
                    "numero": parcela.numero,
                    "vencimento": (
                        parcela.vencimento.isoformat() if parcela.vencimento else None
                    ),
                    "valor": str(parcela.valor),
                    "iof": str(parcela.iof),
                    "custo_apolice": str(parcela.custo_apolice),
                    "adicional_fracionamento": str(parcela.adicional_fracionamento),
                }
                for parcela in opcao.parcelas
            ],
        }
        for opcao in opcoes
    ]


def _snapshot(cotacao: Cotacao) -> dict:
    """O que foi efetivamente enviado à seguradora.

    Os passos seguintes comparam a cotação atual com isto: sem a comparação, o
    usuário edita a IS depois de cotar, vê o número novo na tela e emite o
    número velho na seguradora.
    """
    return {
        "importancia_segurada": str(cotacao.importancia_segurada),
        "prazo_dias": cotacao.prazo_dias,
        "data_inicio": cotacao.data_inicio.isoformat(),
        "modalidade_id": cotacao.modalidade_id,
        "tomador_cnpj": so_digitos(cotacao.tomador.cnpj),
    }


def _validar_para_cotar(cotacao: Cotacao, seguradora: Seguradora) -> None:
    if cotacao.status != Cotacao.STATUS_APROVADO:
        raise ValidationError("A cotação precisa estar aprovada para emitir a apólice.")

    if Apolice.objects.filter(cotacao=cotacao).exists():
        raise ValidationError("Esta cotação já tem apólice emitida.")

    if not (seguradora.integracao or "").strip():
        raise ValidationError(
            "Esta seguradora não tem emissão integrada; use a emissão manual."
        )
    if (
        not (seguradora.api_client_id or "").strip()
        or not (seguradora.api_client_secret or "").strip()
    ):
        raise ValidationError("Credenciais da seguradora não configuradas.")

    if not so_digitos(cotacao.tomador.cnpj):
        raise ValidationError("O tomador precisa de CNPJ para cotar na seguradora.")
    if cotacao.importancia_segurada is None:
        raise ValidationError("Informe a importância segurada antes de cotar.")
    if cotacao.data_inicio is None:
        raise ValidationError("Informe a data de início da vigência antes de cotar.")
    if not cotacao.prazo_dias:
        raise ValidationError("Informe o prazo em dias antes de cotar.")


@transaction.atomic
def emissao_cotar(
    *, cotacao_id: int, seguradora_id: int, conector=None
) -> EmissaoSeguradora:
    """Passo 1: cria (ou recalcula) a cotação na seguradora informada.

    A seguradora vem por argumento, e não de `cotacao.seguradora`, porque
    cotar e escolher são ações diferentes: dá para cotar em três e decidir
    depois. Quem escolhe é o clique no card, que grava `cotacao.seguradora`.

    O lock é na `Cotacao` e não na `EmissaoSeguradora` porque na primeira
    chamada a emissão ainda não existe. Sem ele, dois cliques rápidos na lupa
    viram duas cotações lá dentro, e a segunda fica órfã contando contra o
    limite do tomador.
    """
    cotacao = Cotacao.objects.select_for_update().get(pk=cotacao_id)
    seguradora = Seguradora.objects.get(pk=seguradora_id)
    _validar_para_cotar(cotacao, seguradora)

    emissao = EmissaoSeguradora.objects.filter(
        cotacao=cotacao, seguradora=seguradora
    ).first()

    if (
        emissao is not None
        and emissao.ambiente
        and emissao.ambiente != seguradora.api_ambiente
    ):
        # Um external_id de sandbox não resolve em produção. Enquanto nada foi
        # gerado além da cotação, recomeçar é seguro e evita deixar o usuário
        # num beco sem saída; da minuta em diante, recusamos.
        if emissao.etapa != EmissaoSeguradora.ETAPA_COTADA:
            raise ValidationError(
                "A emissão foi iniciada em outro ambiente e já passou da cotação. "
                "Cancele a emissão na seguradora antes de recomeçar."
            )
        emissao.external_id = ""

    try:
        codigo = codigo_para_seguradora(
            modalidade=cotacao.modalidade, seguradora=seguradora
        )
    except ModalidadeNaoMapeada as exc:
        raise ValidationError(str(exc)) from None

    dados = DadosCotacao(
        modalidade_codigo=codigo,
        tomador_cnpj=cotacao.tomador.cnpj,
        importancia_segurada=cotacao.importancia_segurada,
        data_inicio=cotacao.data_inicio,
        prazo_dias=cotacao.prazo_dias,
        vencimento_primeira_parcela=vencimento_boleto_default(
            cotacao=cotacao, seguradora=seguradora
        ),
    )

    if conector is None:
        try:
            conector = get_conector(seguradora)
        except IntegracaoNaoSuportada as exc:
            raise ValidationError(str(exc)) from None

    if emissao is not None and emissao.external_id:
        resposta = conector.atualizar_cotacao(
            external_id=emissao.external_id, dados=dados
        )
    else:
        resposta = conector.cotar(dados=dados)

    if emissao is None:
        emissao = EmissaoSeguradora(cotacao=cotacao, seguradora=seguradora)

    emissao.seguradora = seguradora
    emissao.integracao = seguradora.integracao
    emissao.ambiente = seguradora.api_ambiente
    emissao.etapa = EmissaoSeguradora.ETAPA_COTADA
    emissao.external_id = resposta.external_id
    emissao.premio_liquido = _quantizar(resposta.premio_liquido, 2)
    emissao.premio_total = _quantizar(resposta.premio_total, 2)
    emissao.taxa = _quantizar(resposta.taxa, 6)
    emissao.comissao_percentual = _quantizar(resposta.comissao_percentual, 2)
    emissao.comissao_valor = _quantizar(resposta.comissao_valor, 2)
    emissao.numero_parcelas = resposta.numero_parcelas
    emissao.numero_max_parcelas = resposta.numero_max_parcelas
    emissao.opcoes_parcelamento = _opcoes_para_json(resposta.opcoes_parcelamento)
    emissao.url_cotacao = resposta.url_cotacao or ""
    emissao.dados_cotados = _snapshot(cotacao)
    emissao.ultimo_request = resposta.request_bruto
    emissao.ultima_resposta = resposta.resposta_bruta
    emissao.codigo_retorno = ""
    emissao.mensagem = ""
    emissao.save()
    return emissao
