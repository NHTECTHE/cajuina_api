from typing import Any, Dict, Optional

from django.core.exceptions import ValidationError

from .models import Cotacao


def cotacao_create(*, data: Dict[str, Any], criado_por: Optional[object] = None) -> Cotacao:
    cotacao = Cotacao(**data)
    if criado_por is not None and getattr(criado_por, "is_authenticated", False):
        cotacao.criado_por = criado_por
    cotacao.save()
    return cotacao


def cotacao_update(*, cotacao: Cotacao, data: Dict[str, Any]) -> Cotacao:
    for field, value in data.items():
        setattr(cotacao, field, value)
    cotacao.save()
    return cotacao


def cotacao_delete(*, cotacao: Cotacao) -> None:
    cotacao.delete()


def cotacao_aprovar(*, cotacao: Cotacao) -> Cotacao:
    if cotacao.status != Cotacao.STATUS_INICIADO:
        raise ValidationError("Esta cotação já foi aprovada.")
    cotacao.status = Cotacao.STATUS_APROVADO
    cotacao.save(update_fields=["status", "atualizado_em"])
    return cotacao
