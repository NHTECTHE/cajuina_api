from decimal import Decimal

from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.dashboard import selectors


def _serializar(valor):
    """Decimal vira string na resposta.

    O JSONRenderer do DRF converteria Decimal para float, e dinheiro em ponto
    flutuante arredonda errado. Os selectors seguem trabalhando com Decimal;
    a conversão acontece só na borda HTTP.
    """
    if isinstance(valor, Decimal):
        return str(valor)
    if isinstance(valor, dict):
        return {chave: _serializar(item) for chave, item in valor.items()}
    if isinstance(valor, list):
        return [_serializar(item) for item in valor]
    return valor


def _envelope(data) -> dict:
    return {"data": _serializar(data)}


def _int_ou(padrao: int, valor: str) -> int:
    """Query params são texto livre; lixo vira o padrão em vez de 500."""
    try:
        return int(valor)
    except (TypeError, ValueError):
        return padrao


class DashboardResumoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        periodo = request.query_params.get("periodo", selectors.PERIODO_PADRAO)
        return Response(_envelope(selectors.resumo(periodo=periodo)))


class DashboardComissoesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        return Response(_envelope(selectors.comissoes()))


class DashboardPremioSeguradorasView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        ano = _int_ou(0, request.query_params.get("ano", "")) or None
        return Response(_envelope(selectors.premio_por_seguradora(ano=ano)))


class DashboardNovosCadastrosView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        dados = selectors.novos_cadastros(
            search=request.query_params.get("search", ""),
            page=_int_ou(1, request.query_params.get("page", "")),
            page_size=_int_ou(
                selectors.PAGE_SIZE_PADRAO, request.query_params.get("page_size", "")
            ),
        )
        return Response(_envelope(dados))
