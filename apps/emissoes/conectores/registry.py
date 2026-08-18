"""Resolve `Seguradora.integracao` para a classe de conector."""

from .base import IntegracaoNaoSuportada
from .junto import ConectorJunto

CONECTORES = {
    ConectorJunto.integracao: ConectorJunto,
}


def get_conector(seguradora, **kwargs):
    chave = (seguradora.integracao or "").strip().lower()
    if not chave:
        raise IntegracaoNaoSuportada(
            "Esta seguradora não tem emissão integrada; use a emissão manual."
        )
    try:
        classe = CONECTORES[chave]
    except KeyError:
        raise IntegracaoNaoSuportada(
            f"Não há conector para a integração '{chave}'."
        ) from None
    return classe(seguradora, **kwargs)
