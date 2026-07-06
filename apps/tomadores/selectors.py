from django.db.models import Q, QuerySet
from .models import Tomador, TomadorArquivo


def tomador_list(
    *,
    search: str = "",
    uf: str = "",
    tipo: str = "",
) -> QuerySet[Tomador]:
    qs = Tomador.objects.prefetch_related("contatos_adicionais", "socios")

    if search:
        qs = qs.filter(
            Q(nome__icontains=search)
            | Q(cnpj__icontains=search)
            | Q(contato__icontains=search)
        )

    if uf:
        qs = qs.filter(uf__iexact=uf)

    if tipo == "CNPJ":
        qs = qs.filter(cnpj__contains="/")
    elif tipo == "CPF":
        qs = qs.exclude(cnpj__contains="/")

    return qs


def tomador_get(*, pk: int) -> Tomador:
    return Tomador.objects.prefetch_related("contatos_adicionais", "socios").get(pk=pk)


def tomador_arquivo_list(*, tomador_id: int) -> QuerySet[TomadorArquivo]:
    return TomadorArquivo.objects.filter(tomador_id=tomador_id)


def tomador_arquivo_get(*, tomador_id: int, pk: int) -> TomadorArquivo:
    return TomadorArquivo.objects.get(tomador_id=tomador_id, pk=pk)
