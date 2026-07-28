from django.db.models import Q, QuerySet

from .models import Tomador, TomadorArquivo, TomadorSeguradora


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


def tomador_seguradora_list(*, tomador_id: int) -> QuerySet[TomadorSeguradora]:
    return TomadorSeguradora.objects.filter(
        tomador_id=tomador_id
    ).select_related("seguradora")


def tomador_seguradora_get(*, tomador_id: int, seguradora_id: int) -> TomadorSeguradora:
    return TomadorSeguradora.objects.select_related("seguradora").get(
        tomador_id=tomador_id, seguradora_id=seguradora_id
    )


def tomador_seguradora_aptas(*, tomador_id: int) -> QuerySet[TomadorSeguradora]:
    """Pares utilizáveis em cotação: taxa positiva e seguradora ativa."""
    return TomadorSeguradora.objects.filter(
        tomador_id=tomador_id,
        taxa__gt=0,
        seguradora__ativo=True,
    ).select_related("seguradora")
