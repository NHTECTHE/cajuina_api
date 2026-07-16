from typing import Any, Dict, Optional

from django.core.exceptions import ValidationError

from .models import Cotacao
from apps.notificacoes.models import Notificacao
from django.contrib.auth import get_user_model


def cotacao_create(*, data: Dict[str, Any], criado_por: Optional[object] = None) -> Cotacao:
    cotacao = Cotacao(**data)
    if criado_por is not None and getattr(criado_por, "is_authenticated", False):
        cotacao.criado_por = criado_por
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
