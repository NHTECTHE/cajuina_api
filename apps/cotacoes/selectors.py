from collections.abc import Iterable

from django.db.models import Q

from .models import Cotacao


def _base_qs():
    # `emissoes` entra no prefetch por causa de `premio_seguradora` no
    # serializer: sem ele a listagem faz uma consulta por cotação.
    return Cotacao.objects.select_related(
        "tomador", "modalidade", "segurado", "criado_por"
    ).prefetch_related("emissoes")


def cotacao_list(*, search: str = "", status: str = "") -> Iterable[Cotacao]:
    qs = _base_qs()
    if search:
        qs = qs.filter(
            Q(tomador__nome__icontains=search)
            | Q(tomador__cnpj__icontains=search)
            | Q(modalidade__nome__icontains=search)
            | Q(edital__icontains=search)
        )
    if status:
        qs = qs.filter(status=status)
    return qs


def cotacao_get(*, pk: int) -> Cotacao:
    return _base_qs().get(pk=pk)
