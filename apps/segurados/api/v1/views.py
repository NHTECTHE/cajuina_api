from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from apps.segurados import selectors, services
from apps.segurados.models import Segurado
from .serializers import SeguradoSerializer


def _envelope(data) -> dict:
    return {"data": data}


class SeguradoListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        search = request.query_params.get("search", "")
        segurados = selectors.segurado_list(search=search)
        serializer = SeguradoSerializer(segurados, many=True)
        return Response(_envelope(serializer.data))

    def post(self, request: Request) -> Response:
        serializer = SeguradoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        segurado = services.segurado_create(data=serializer.validated_data)
        out = SeguradoSerializer(segurado)
        return Response(_envelope(out.data), status=status.HTTP_201_CREATED)


class SeguradoDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_object(self, pk: int) -> Segurado:
        try:
            return selectors.segurado_get(pk=pk)
        except Segurado.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound(detail="Segurado não encontrado.")

    def get(self, request: Request, pk: int) -> Response:
        segurado = self._get_object(pk)
        serializer = SeguradoSerializer(segurado)
        return Response(_envelope(serializer.data))

    def patch(self, request: Request, pk: int) -> Response:
        segurado = self._get_object(pk)
        serializer = SeguradoSerializer(segurado, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        segurado = services.segurado_update(segurado=segurado, data=serializer.validated_data)
        out = SeguradoSerializer(segurado)
        return Response(_envelope(out.data))

    def delete(self, request: Request, pk: int) -> Response:
        segurado = self._get_object(pk)
        services.segurado_delete(segurado=segurado)
        return Response(status=status.HTTP_204_NO_CONTENT)
