from typing import Iterable

from django.db.models import Q

from .models import Cotacao


def _base_qs():
    return Cotacao.objects.select_related(
        "tomador", "modalidade", "segurado", "criado_por"
    )


def cotacao_list(*, search: str = "") -> Iterable[Cotacao]:
    qs = _base_qs()
    if search:
        qs = qs.filter(
            Q(tomador__nome__icontains=search)
            | Q(tomador__cnpj__icontains=search)
            | Q(modalidade__nome__icontains=search)
            | Q(edital__icontains=search)
        )
    return qs


def cotacao_get(*, pk: int) -> Cotacao:
    return _base_qs().get(pk=pk)
