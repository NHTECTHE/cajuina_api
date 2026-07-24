from typing import Any, Dict

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Modalidade, ModalidadeSeguradora


def modalidade_create(*, data: Dict[str, Any]) -> Modalidade:
    modalidade = Modalidade(**data)
    modalidade.save()
    return modalidade


def modalidade_update(*, modalidade: Modalidade, data: Dict[str, Any]) -> Modalidade:
    for field, value in data.items():
        setattr(modalidade, field, value)
    modalidade.save()
    return modalidade


def modalidade_delete(*, modalidade: Modalidade) -> None:
    """Exclui a modalidade, desde que nenhuma cotação dependa dela.

    A FK da Cotacao é PROTECT: sem esta checagem o banco levanta ProtectedError
    e a API devolve 500. Checando antes, o operador recebe 400 com a saída.
    """
    if modalidade.cotacoes.exists():
        raise ValidationError(
            "Modalidade com cotações vinculadas não pode ser excluída. "
            "Desative-a para tirá-la de circulação."
        )
    modalidade.delete()


# ─── Mapeamento modalidade × seguradora ──────────────────────────────────────


def modalidade_seguradora_upsert(
    *, modalidade: Modalidade, seguradora, data: dict
) -> ModalidadeSeguradora:
    """Cria ou atualiza o código da modalidade naquela seguradora.

    A UniqueConstraint do par permite um único update_or_create — no legado
    isso era um `get` seguido de `if/else` com insert e update duplicados.
    """
    vinculo, _ = ModalidadeSeguradora.objects.update_or_create(
        modalidade=modalidade,
        seguradora=seguradora,
        defaults=data,
    )
    return vinculo


def modalidade_seguradora_delete(*, vinculo: ModalidadeSeguradora) -> None:
    vinculo.delete()


@transaction.atomic
def modalidade_seguradora_bulk_upsert(
    *, modalidade: Modalidade, itens: list[dict]
) -> list[ModalidadeSeguradora]:
    """Salva os códigos de várias seguradoras para uma modalidade.

    Código em branco remove o mapeamento: é assim que a tela marca "esta
    seguradora não oferece esta modalidade". Seguradoras fora do payload ficam
    intactas.
    """
    resultado = []
    for item in itens:
        data = dict(item)
        seguradora = data.pop("seguradora")
        codigo = (data.get("codigo_seguradora") or "").strip()

        if not codigo:
            ModalidadeSeguradora.objects.filter(
                modalidade=modalidade, seguradora=seguradora
            ).delete()
            continue

        data["codigo_seguradora"] = codigo
        resultado.append(
            modalidade_seguradora_upsert(
                modalidade=modalidade, seguradora=seguradora, data=data
            )
        )
    return resultado


@transaction.atomic
def matriz_salvar(*, linhas: list[dict]) -> None:
    """Salva a matriz inteira de modalidades × seguradoras.

    A tela edita várias células e salva de uma vez, como o `/modalidade_seguradoras`
    do sistema antigo fazia. Atômico: uma célula inválida não deixa a matriz
    meio gravada.
    """
    for linha in linhas:
        modalidade_seguradora_bulk_upsert(
            modalidade=linha["modalidade"],
            itens=linha["itens"],
        )
