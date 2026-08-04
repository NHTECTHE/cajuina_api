from collections.abc import Iterable

from django.db.models import Q

from .models import Apolice


def _base_qs():
    return Apolice.objects.select_related(
        "cotacao", "cotacao__tomador", "seguradora", "emitido_por"
    )


def apolice_list(*, search: str = "", tomador_id: int | None = None) -> Iterable[Apolice]:
    qs = _base_qs()
    if tomador_id is not None:
        qs = qs.filter(cotacao__tomador_id=tomador_id)
    if search:
        qs = qs.filter(
            Q(numero_apolice__icontains=search)
            | Q(cotacao__tomador__nome__icontains=search)
            | Q(cotacao__tomador__cnpj__icontains=search)
            | Q(seguradora__nome__icontains=search)
        )
    return qs


def apolice_get(*, pk: int) -> Apolice:
    return _base_qs().get(pk=pk)


def apolice_get_by_cotacao(*, cotacao_id: int) -> Apolice:
    return _base_qs().get(cotacao_id=cotacao_id)
