from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from apps.seguradoras import selectors, services
from apps.seguradoras.models import Seguradora
from .serializers import SeguradoraSerializer


def _envelope(data) -> dict:
    return {"data": data}


class SeguradoraListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        search = request.query_params.get("search", "")
        ativo = request.query_params.get("ativo", "")
        seguradoras = selectors.seguradora_list(search=search, ativo=ativo)
        serializer = SeguradoraSerializer(seguradoras, many=True)
        return Response(_envelope(serializer.data))

    def post(self, request: Request) -> Response:
        serializer = SeguradoraSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        seguradora = services.seguradora_create(data=serializer.validated_data)
        out = SeguradoraSerializer(seguradora)
        return Response(_envelope(out.data), status=status.HTTP_201_CREATED)


class SeguradoraDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_object(self, pk: int) -> Seguradora:
        try:
            return selectors.seguradora_get(pk=pk)
        except Seguradora.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound(detail="Seguradora não encontrada.")

    def get(self, request: Request, pk: int) -> Response:
        seguradora = self._get_object(pk)
        serializer = SeguradoraSerializer(seguradora)
        return Response(_envelope(serializer.data))

    def patch(self, request: Request, pk: int) -> Response:
        seguradora = self._get_object(pk)
        serializer = SeguradoraSerializer(seguradora, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        seguradora = services.seguradora_update(seguradora=seguradora, data=serializer.validated_data)
        out = SeguradoraSerializer(seguradora)
        return Response(_envelope(out.data))

    def delete(self, request: Request, pk: int) -> Response:
        seguradora = self._get_object(pk)
        services.seguradora_delete(seguradora=seguradora)
        return Response(status=status.HTTP_204_NO_CONTENT)
