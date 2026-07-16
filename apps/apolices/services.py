from typing import Any, Dict, Optional

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.cotacoes.models import Cotacao
from apps.notificacoes.models import Notificacao
from django.contrib.auth import get_user_model

from .models import Apolice


@transaction.atomic
def apolice_emitir(
    *, cotacao: Cotacao, data: Dict[str, Any], emitido_por: Optional[object] = None
) -> Apolice:
    if cotacao.status != Cotacao.STATUS_APROVADO:
        raise ValidationError("A cotação precisa estar aprovada para emitir a apólice.")

    apolice = Apolice(cotacao=cotacao, **data)
    if emitido_por is not None and getattr(emitido_por, "is_authenticated", False):
        apolice.emitido_por = emitido_por
    apolice.save()

    cotacao.status = Cotacao.STATUS_EMITIDO
    cotacao.save(update_fields=["status", "atualizado_em"])

    User = get_user_model()
    users_to_notify = User.objects.all()
    nome_exibicao = cotacao.tomador.nome_fantasia if cotacao.tomador.nome_fantasia else cotacao.tomador.nome
    for user in users_to_notify:
        Notificacao.objects.create(
            usuario=user,
            titulo="Nova apólice emitida",
            status_badge="APÓLICE",
            mensagem=nome_exibicao
        )

    return apolice
