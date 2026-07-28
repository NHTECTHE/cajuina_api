from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from apps.notificacoes.models import Notificacao
from apps.tomadores.models import TomadorSeguradora

from .models import Cotacao

DIAS_NO_ANO = Decimal("365")


def _quantizar(valor) -> Decimal:
    return Decimal(valor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


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

    calculado = (
        (Decimal(cotacao.importancia_segurada) / DIAS_NO_ANO)
        * (Decimal(taxa or 0) / Decimal("100"))
        * Decimal(cotacao.prazo_dias)
    )
    return _quantizar(max(calculado, Decimal(premio_minimo)))


def cotacao_create(*, data: dict[str, Any], criado_por: object | None = None) -> Cotacao:
    cotacao = Cotacao(**data)
    if criado_por is not None and getattr(criado_por, "is_authenticated", False):
        cotacao.criado_por = criado_por
    cotacao.premio = cotacao_calcular_premio(cotacao=cotacao)
    cotacao.save()

    User = get_user_model()
    users_to_notify = User.objects.all()
    nome_exibicao = cotacao.tomador.nome_fantasia if cotacao.tomador.nome_fantasia else cotacao.tomador.nome
    for user in users_to_notify:
        Notificacao.objects.create(
            usuario=user,
            titulo="Nova cotação solicitada",
            status_badge="COTAÇÃO",
            mensagem=nome_exibicao
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


def cotacao_aprovar(*, cotacao: Cotacao) -> Cotacao:
    if cotacao.status != Cotacao.STATUS_INICIADO:
        raise ValidationError("Esta cotação já foi aprovada.")
    cotacao.status = Cotacao.STATUS_APROVADO
    cotacao.save(update_fields=["status", "atualizado_em"])

    User = get_user_model()
    users_to_notify = User.objects.all()
    nome_exibicao = cotacao.tomador.nome_fantasia if cotacao.tomador.nome_fantasia else cotacao.tomador.nome
    for user in users_to_notify:
        Notificacao.objects.create(
            usuario=user,
            titulo="Nova proposta gerada",
            status_badge="PROPOSTA",
            mensagem=nome_exibicao
        )

    return cotacao
