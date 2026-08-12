from decimal import Decimal


def formatar_brl(valor) -> str:
    """Formata em Real no padrão pt-BR: 1234.5 -> 'R$ 1.234,50'."""
    if valor is None:
        return "—"
    quantizado = Decimal(valor).quantize(Decimal("0.01"))
    inteiro, _, centavos = f"{quantizado:.2f}".partition(".")
    negativo = inteiro.startswith("-")
    inteiro = inteiro.lstrip("-")
    grupos = []
    while len(inteiro) > 3:
        grupos.insert(0, inteiro[-3:])
        inteiro = inteiro[:-3]
    grupos.insert(0, inteiro)
    return f"{'-' if negativo else ''}R$ {'.'.join(grupos)},{centavos}"


def formatar_data(valor) -> str:
    """Data no padrão pt-BR, ou travessão quando ausente."""
    return valor.strftime("%d/%m/%Y") if valor else "—"
