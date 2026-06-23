from .models import Corretor


def corretor_list(*, search: str = "", ativo: str = "") -> list:
    qs = Corretor.objects.all()
    if search:
        qs = qs.filter(nome__icontains=search) | qs.filter(cpf_cnpj__icontains=search)
    if ativo in ("true", "false"):
        qs = qs.filter(ativo=ativo == "true")
    return qs.distinct()


def corretor_get(*, pk: int) -> Corretor:
    return Corretor.objects.get(pk=pk)
