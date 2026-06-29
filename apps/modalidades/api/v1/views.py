from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from apps.modalidades import selectors, services
from apps.modalidades.models import Modalidade
from .serializers import ModalidadeSerializer


def _envelope(data) -> dict:
    return {"data": data}


class ModalidadeListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        search = request.query_params.get("search", "")
        ativo = request.query_params.get("ativo", "")
        modalidades = selectors.modalidade_list(search=search, ativo=ativo)
        serializer = ModalidadeSerializer(modalidades, many=True)
        return Response(_envelope(serializer.data))

    def post(self, request: Request) -> Response:
        serializer = ModalidadeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        modalidade = services.modalidade_create(data=serializer.validated_data)
        out = ModalidadeSerializer(modalidade)
        return Response(_envelope(out.data), status=status.HTTP_201_CREATED)


class ModalidadeDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_object(self, pk: int) -> Modalidade:
        try:
            return selectors.modalidade_get(pk=pk)
        except Modalidade.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound(detail="Modalidade não encontrada.")

    def get(self, request: Request, pk: int) -> Response:
        modalidade = self._get_object(pk)
        serializer = ModalidadeSerializer(modalidade)
        return Response(_envelope(serializer.data))

    def patch(self, request: Request, pk: int) -> Response:
        modalidade = self._get_object(pk)
        serializer = ModalidadeSerializer(modalidade, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        modalidade = services.modalidade_update(modalidade=modalidade, data=serializer.validated_data)
        out = ModalidadeSerializer(modalidade)
        return Response(_envelope(out.data))

    def delete(self, request: Request, pk: int) -> Response:
        modalidade = self._get_object(pk)
        services.modalidade_delete(modalidade=modalidade)
        return Response(status=status.HTTP_204_NO_CONTENT)
