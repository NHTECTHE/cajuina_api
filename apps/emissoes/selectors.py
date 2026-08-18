from decimal import Decimal

from .models import EmissaoSeguradora


def emissoes_listar_por_cotacao(*, cotacao_id: int):
    """Todas as seguradoras já cotadas nesta cotação."""
    return EmissaoSeguradora.objects.select_related("seguradora", "cotacao").filter(
        cotacao_id=cotacao_id
    )


def premios_cotados_por_seguradora(*, cotacao_id: int) -> dict[int, Decimal]:
    """Mapa `seguradora_id -> prêmio total real`, só das que já foram cotadas.

    É o que permite ao e-mail e ao PDF preferirem o número da seguradora à
    nossa estimativa, sem uma consulta por seguradora.
    """
    return {
        emissao.seguradora_id: emissao.premio_total
        for emissao in EmissaoSeguradora.objects.filter(
            cotacao_id=cotacao_id, premio_total__isnull=False
        )
    }
