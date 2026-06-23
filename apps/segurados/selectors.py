from django.db.models import Q
from .models import Segurado


def segurado_list(*, search: str = "") -> list:
    qs = Segurado.objects.all()
    if search:
        qs = qs.filter(Q(nome__icontains=search) | Q(cnpj__icontains=search))
    return qs


def segurado_get(*, pk: int) -> Segurado:
    return Segurado.objects.get(pk=pk)
