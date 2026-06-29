from typing import Iterable
from .models import Modalidade

def modalidade_list(*, search: str = "", ativo: str = "") -> Iterable[Modalidade]:
    qs = Modalidade.objects.all()
    if search:
        qs = qs.filter(nome__icontains=search)
    if ativo:
        if ativo.lower() in ["true", "1", "sim", "t", "y", "yes"]:
            qs = qs.filter(ativo=True)
        elif ativo.lower() in ["false", "0", "nao", "f", "n", "no"]:
            qs = qs.filter(ativo=False)
    return qs

def modalidade_get(*, pk: int) -> Modalidade:
    return Modalidade.objects.get(pk=pk)
