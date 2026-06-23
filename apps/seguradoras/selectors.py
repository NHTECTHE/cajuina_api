from .models import Seguradora


def seguradora_list(*, search: str = "", ativo: str = "") -> list:
    qs = Seguradora.objects.all()
    if search:
        qs = qs.filter(nome__icontains=search)
    if ativo in ("true", "false"):
        qs = qs.filter(ativo=ativo == "true")
    return qs


def seguradora_get(*, pk: int) -> Seguradora:
    return Seguradora.objects.get(pk=pk)
