from .models import Produtor


def produtor_list(*, search: str = "", ativo: str = "") -> list:
    qs = Produtor.objects.select_related("corretora")
    if search:
        qs = qs.filter(nome__icontains=search) | qs.filter(corretora__nome__icontains=search)
    if ativo in ("true", "false"):
        qs = qs.filter(ativo=ativo == "true")
    return qs.distinct()


def produtor_get(*, pk: int) -> Produtor:
    return Produtor.objects.get(pk=pk)
