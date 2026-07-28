from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.apolices import selectors, services
from apps.apolices.models import Apolice
from apps.cotacoes import selectors as cotacoes_selectors
from apps.cotacoes.models import Cotacao

from .serializers import ApoliceSerializer


def _envelope(data) -> dict:
    return {"data": data}


class CotacaoEmitirView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request: Request, pk: int) -> Response:
        try:
            cotacao = cotacoes_selectors.cotacao_get(pk=pk)
        except Cotacao.DoesNotExist:
            raise NotFound(detail="Cotação não encontrada.") from None

        serializer = ApoliceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            apolice = services.apolice_emitir(
                cotacao=cotacao,
                data=serializer.validated_data,
                emitido_por=request.user,
            )
        except ValidationError as exc:
            return Response(
                {"detail": exc.messages[0]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        out = ApoliceSerializer(apolice)
        return Response(_envelope(out.data), status=status.HTTP_201_CREATED)


class ApoliceListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        search = request.query_params.get("search", "")
        apolices = selectors.apolice_list(search=search)
        serializer = ApoliceSerializer(apolices, many=True)
        return Response(_envelope(serializer.data))


class ApoliceDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, pk: int) -> Response:
        try:
            apolice = selectors.apolice_get(pk=pk)
        except Apolice.DoesNotExist:
            raise NotFound(detail="Apólice não encontrada.") from None
        serializer = ApoliceSerializer(apolice)
        return Response(_envelope(serializer.data))
