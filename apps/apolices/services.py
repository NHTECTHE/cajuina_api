from datetime import date, timedelta
from typing import Any

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.cotacoes.models import Cotacao
from apps.notificacoes.models import Notificacao
from apps.tomadores.models import TomadorSeguradora
from shared.utils import formatar_brl, formatar_data

from .models import Apolice


def vencimento_boleto_default(*, cotacao: Cotacao, seguradora) -> date | None:
    """Data sugerida do boleto: hoje + dias_vencimento_efetivo do par
    tomador x seguradora, com fallback para o vencimento da própria
    seguradora (embutido em dias_vencimento_efetivo).

    Pública porque `apps.emissoes.services` a usa para montar o
    `dueDateFirstInstallment` da seguradora: a regra do par tomador x
    seguradora vale nas duas portas de emissão, a manual e a integrada."""
    try:
        vinculo = TomadorSeguradora.objects.get(
            tomador_id=cotacao.tomador_id, seguradora=seguradora
        )
        dias = vinculo.dias_vencimento_efetivo
    except TomadorSeguradora.DoesNotExist:
        dias = seguradora.vencimento_dias

    if dias is None:
        return None
    return date.today() + timedelta(days=dias)


@transaction.atomic
def apolice_emitir(
    *, cotacao: Cotacao, data: dict[str, Any], emitido_por: object | None = None
) -> Apolice:
    if cotacao.status != Cotacao.STATUS_APROVADO:
        raise ValidationError("A cotação precisa estar aprovada para emitir a apólice.")

    if data.get("vencimento_boleto") is None:
        data = {
            **data,
            "vencimento_boleto": vencimento_boleto_default(
                cotacao=cotacao, seguradora=data["seguradora"]
            ),
        }

    apolice = Apolice(cotacao=cotacao, **data)
    if emitido_por is not None and getattr(emitido_por, "is_authenticated", False):
        apolice.emitido_por = emitido_por
    apolice.save()

    cotacao.status = Cotacao.STATUS_EMITIDO
    cotacao.save(update_fields=["status", "atualizado_em"])

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
            titulo="Nova apólice emitida",
            status_badge="APÓLICE",
            mensagem=nome_exibicao,
        )

    return apolice


def apolice_update(*, apolice: Apolice, data: dict[str, Any]) -> Apolice:
    for field, value in data.items():
        setattr(apolice, field, value)
    apolice.save()
    return apolice


@transaction.atomic
def apolice_delete(*, apolice: Apolice) -> None:
    # Se a apólice é excluída, a cotação volta para o status de aprovada
    cotacao = apolice.cotacao
    cotacao.status = Cotacao.STATUS_APROVADO
    cotacao.save(update_fields=["status", "atualizado_em"])
    apolice.delete()


def apolice_montar_email(*, apolice: Apolice, observacao: str = "") -> dict[str, str]:
    """Assunto, destinatário e corpo do e-mail de apólice emitida.

    Mesma regra de `cotacao_montar_email`: o conteúdo sai do objeto, e o cliente
    só pode acrescentar uma observação identificada.
    """
    cotacao = apolice.cotacao
    tomador = cotacao.tomador
    segurado = cotacao.segurado.nome if cotacao.segurado_id else tomador.nome

    corpo = f"""Prezado(a),

Sua apólice foi emitida com sucesso.

Detalhes:
- Apólice: {apolice.numero_apolice}
- Segurado: {segurado}
- Seguradora: {apolice.seguradora.nome}
- Prêmio: {formatar_brl(apolice.valor_seguradora)}
- Vencimento do boleto: {formatar_data(apolice.vencimento_boleto)}"""

    if observacao:
        corpo += f"\n\n**Observações**\n\n{observacao}"

    corpo += """

Atenciosamente,
Equipe Cajuína Seguros."""

    return {
        "assunto": "Apólice Emitida",
        "destinatario": tomador.email,
        "mensagem": corpo,
    }
