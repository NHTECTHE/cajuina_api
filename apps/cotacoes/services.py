from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from django.contrib.auth import get_user_model

from apps.emissoes.selectors import premios_cotados_por_seguradora
from apps.notificacoes.models import Notificacao
from apps.tomadores.models import TomadorSeguradora
from apps.tomadores.selectors import tomador_seguradora_aptas
from shared.utils import formatar_brl

from .models import Cotacao

DIAS_NO_ANO = Decimal("365")


def _quantizar(valor) -> Decimal:
    return Decimal(valor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _premio_pro_rata(
    *, importancia_segurada, prazo_dias, taxa, premio_minimo
) -> Decimal:
    """(IS / 365) * (taxa / 100) * prazo, com piso no prêmio mínimo."""
    calculado = (
        (Decimal(importancia_segurada) / DIAS_NO_ANO)
        * (Decimal(taxa or 0) / Decimal("100"))
        * Decimal(prazo_dias)
    )
    return _quantizar(max(calculado, Decimal(premio_minimo)))


def cotacao_calcular_premio(*, cotacao: Cotacao) -> Decimal | None:
    """Prêmio pro rata temporis da cotação.

    (importancia_segurada / 365) * (taxa / 100) * prazo_dias, com piso no
    prêmio mínimo do par tomador x seguradora (que por sua vez herda o da
    seguradora quando não definido).

    Retorna None quando não há seguradora escolhida ou faltam dados de cálculo.
    """
    if cotacao.seguradora_id is None:
        return None

    try:
        vinculo = TomadorSeguradora.objects.get(
            tomador_id=cotacao.tomador_id, seguradora_id=cotacao.seguradora_id
        )
        taxa = vinculo.taxa
        premio_minimo = vinculo.premio_minimo_efetivo
    except TomadorSeguradora.DoesNotExist:
        # Sem condições cadastradas para o par: não há taxa, só o piso da seguradora.
        taxa = None
        premio_minimo = cotacao.seguradora.premio_minimo

    if cotacao.importancia_segurada is None or not cotacao.prazo_dias:
        # Sem base de cálculo não há prêmio a apurar; o piso sozinho não é cotação.
        return None if taxa is not None else _quantizar(premio_minimo)

    return _premio_pro_rata(
        importancia_segurada=cotacao.importancia_segurada,
        prazo_dias=cotacao.prazo_dias,
        taxa=taxa,
        premio_minimo=premio_minimo,
    )


def cotacao_create(
    *, data: dict[str, Any], criado_por: object | None = None
) -> Cotacao:
    cotacao = Cotacao(**data)
    if criado_por is not None and getattr(criado_por, "is_authenticated", False):
        cotacao.criado_por = criado_por
    cotacao.premio = cotacao_calcular_premio(cotacao=cotacao)
    cotacao.save()

    User = get_user_model()
    users_to_notify = User.objects.all()
    nome_exibicao = (
        cotacao.tomador.nome_fantasia
        if cotacao.tomador.nome_fantasia
        else cotacao.tomador.nome
    )
    for user in users_to_notify:
        Notificacao.objects.create(
            usuario=user,
            titulo="Nova cotação solicitada",
            status_badge="COTAÇÃO",
            mensagem=nome_exibicao,
        )

    return cotacao


def cotacao_update(*, cotacao: Cotacao, data: dict[str, Any]) -> Cotacao:
    for field, value in data.items():
        setattr(cotacao, field, value)
    # A seguradora, a IS e o prazo alimentam o prêmio: recalcula a cada alteração.
    cotacao.premio = cotacao_calcular_premio(cotacao=cotacao)
    cotacao.save()
    return cotacao


def cotacao_delete(*, cotacao: Cotacao) -> None:
    cotacao.delete()


def _linhas_seguradoras(*, cotacao: Cotacao) -> str:
    """Uma linha por seguradora apta, com o prêmio daquele par.

    Quando já se cotou de verdade naquela seguradora, o número que vai para o
    cliente é o dela, não a nossa estimativa — mandar o valor calculado depois
    de ter o preço real seria mandar um número que ninguém honra.
    """
    if cotacao.importancia_segurada is None or not cotacao.prazo_dias:
        return "Nenhuma seguradora disponível"

    reais = premios_cotados_por_seguradora(cotacao_id=cotacao.pk)

    linhas = [
        f"{vinculo.seguradora.nome}: "
        + formatar_brl(
            reais.get(vinculo.seguradora_id)
            or _premio_pro_rata(
                importancia_segurada=cotacao.importancia_segurada,
                prazo_dias=cotacao.prazo_dias,
                taxa=vinculo.taxa,
                premio_minimo=vinculo.premio_minimo_efetivo,
            )
        )
        for vinculo in tomador_seguradora_aptas(tomador_id=cotacao.tomador_id)
    ]
    return "\n".join(linhas) if linhas else "Nenhuma seguradora disponível"


def cotacao_montar_email(*, cotacao: Cotacao, observacao: str = "") -> dict[str, str]:
    """Assunto, destinatário e corpo do e-mail de cotação.

    Tudo é derivado da própria cotação. O cliente não escolhe destinatário nem
    conteúdo: no máximo acrescenta `observacao`, que entra numa seção própria e
    identificada. É isso que impede o endpoint de virar um relay para enviar
    qualquer texto, para qualquer endereço, com o remetente da corretora.
    """
    tomador = cotacao.tomador
    corpo = f"""Cotação de Seguro Garantia

Olá, {tomador.nome}!

Segue abaixo os dados da sua cotação.

**Dados da Cotação**
Cliente:
{tomador.nome} - {tomador.cnpj}

Edital / Contrato:
{cotacao.edital or "—"}

Modalidade:
{cotacao.modalidade.nome if cotacao.modalidade_id else "—"}

Importância Segurada:
{formatar_brl(cotacao.importancia_segurada)}

Prazo:
{f"{cotacao.prazo_dias} Dias" if cotacao.prazo_dias else "—"}

**Valores das Seguradoras**

{_linhas_seguradoras(cotacao=cotacao)}

Sua cotação já está aprovada e pronta para emissão da apólice."""

    if observacao:
        corpo += f"\n\n**Observações**\n\n{observacao}"

    corpo += """

Caso tenha qualquer dúvida, estamos à disposição.

Atenciosamente,

E-mail: garantia@cajuinaseguros.com.br"""

    return {
        "assunto": "Cotação de Seguro Garantia",
        "destinatario": tomador.email,
        "mensagem": corpo,
    }
