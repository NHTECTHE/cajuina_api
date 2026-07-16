from typing import Any, Dict, Optional

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.cotacoes.models import Cotacao

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

    return apolice
