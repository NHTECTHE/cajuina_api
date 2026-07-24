from django.db.models import QuerySet

from .models import Modalidade, ModalidadeNaoMapeada, ModalidadeSeguradora


def modalidade_list(
    *, search: str = "", ativo: str = "", seguradora: str = ""
) -> QuerySet[Modalidade]:
    qs = Modalidade.objects.all()
    if search:
        qs = qs.filter(nome__icontains=search)
    if ativo:
        if ativo.lower() in ["true", "1", "sim", "t", "y", "yes"]:
            qs = qs.filter(ativo=True)
        elif ativo.lower() in ["false", "0", "nao", "f", "n", "no"]:
            qs = qs.filter(ativo=False)
    if seguradora:
        # Só as modalidades que a seguradora realmente oferece — é o que monta o
        # select de modalidades depois que o operador escolhe a seguradora.
        qs = qs.filter(
            seguradoras__seguradora_id=seguradora,
            seguradoras__ativo=True,
        )
    return qs


def modalidade_get(*, pk: int) -> Modalidade:
    return Modalidade.objects.get(pk=pk)


# ─── Mapeamento modalidade × seguradora ──────────────────────────────────────


def modalidade_seguradora_list(
    *, modalidade_id: int | None = None, seguradora_id: int | None = None
) -> QuerySet[ModalidadeSeguradora]:
    qs = ModalidadeSeguradora.objects.select_related("modalidade", "seguradora")
    if modalidade_id is not None:
        qs = qs.filter(modalidade_id=modalidade_id)
    if seguradora_id is not None:
        qs = qs.filter(seguradora_id=seguradora_id)
    return qs


def modalidade_seguradora_get(
    *, modalidade_id: int, seguradora_id: int
) -> ModalidadeSeguradora:
    return ModalidadeSeguradora.objects.select_related("modalidade", "seguradora").get(
        modalidade_id=modalidade_id, seguradora_id=seguradora_id
    )


def codigo_para_seguradora(*, modalidade, seguradora) -> str:
    """Traduz a modalidade para o código da seguradora.

    Equivale ao `modalidade_seguradora()` do sistema antigo, sem o fallback:
    lá, sem mapeamento, o ID interno seguia no payload e a seguradora cotava
    outra coisa. Aqui a falta de mapeamento levanta `ModalidadeNaoMapeada` e
    quem chama decide se pula a seguradora ou aborta a operação.
    """
    try:
        vinculo = ModalidadeSeguradora.objects.get(
            modalidade=modalidade,
            seguradora=seguradora,
            ativo=True,
        )
    except ModalidadeSeguradora.DoesNotExist:
        raise ModalidadeNaoMapeada(modalidade, seguradora)
    return vinculo.codigo_seguradora


def modalidade_por_codigo(*, seguradora, codigo: str) -> Modalidade:
    """Caminho inverso: do código da seguradora para a modalidade interna.

    Usado ao ler dados que vêm da seguradora (no legado, `api_junto_helper.php`
    fazia isso ao importar apólices).
    """
    try:
        vinculo = ModalidadeSeguradora.objects.select_related("modalidade").get(
            seguradora=seguradora,
            codigo_seguradora=codigo,
            ativo=True,
        )
    except ModalidadeSeguradora.DoesNotExist:
        raise ModalidadeNaoMapeada(f"código {codigo}", seguradora)
    return vinculo.modalidade
