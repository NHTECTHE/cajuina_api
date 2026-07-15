from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cotacoes import selectors, services
from apps.cotacoes.models import Cotacao

from .serializers import CotacaoSerializer


def _envelope(data) -> dict:
    return {"data": data}


class CotacaoListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        search = request.query_params.get("search", "")
        cotacoes = selectors.cotacao_list(search=search)
        serializer = CotacaoSerializer(cotacoes, many=True)
        return Response(_envelope(serializer.data))

    def post(self, request: Request) -> Response:
        serializer = CotacaoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cotacao = services.cotacao_create(
            data=serializer.validated_data,
            criado_por=request.user,
        )
        out = CotacaoSerializer(cotacao)
        return Response(_envelope(out.data), status=status.HTTP_201_CREATED)


class _CotacaoObjectMixin:
    def _get_object(self, pk: int) -> Cotacao:
        try:
            return selectors.cotacao_get(pk=pk)
        except Cotacao.DoesNotExist:
            raise NotFound(detail="Cotação não encontrada.")


class CotacaoDetailView(_CotacaoObjectMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, pk: int) -> Response:
        cotacao = self._get_object(pk)
        serializer = CotacaoSerializer(cotacao)
        return Response(_envelope(serializer.data))

    def patch(self, request: Request, pk: int) -> Response:
        cotacao = self._get_object(pk)
        serializer = CotacaoSerializer(cotacao, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        cotacao = services.cotacao_update(cotacao=cotacao, data=serializer.validated_data)
        out = CotacaoSerializer(cotacao)
        return Response(_envelope(out.data))

    def delete(self, request: Request, pk: int) -> Response:
        cotacao = self._get_object(pk)
        services.cotacao_delete(cotacao=cotacao)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CotacaoAprovarView(_CotacaoObjectMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, pk: int) -> Response:
        cotacao = self._get_object(pk)
        try:
            cotacao = services.cotacao_aprovar(cotacao=cotacao)
        except ValidationError as exc:
            return Response(
                {"detail": exc.messages[0]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = CotacaoSerializer(cotacao)
        return Response(_envelope(serializer.data))
