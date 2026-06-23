from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from apps.corretores import selectors, services
from apps.corretores.models import Corretor
from .serializers import CorretorSerializer


def _envelope(data) -> dict:
    return {"data": data}


class CorretorListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        search = request.query_params.get("search", "")
        ativo = request.query_params.get("ativo", "")
        corretores = selectors.corretor_list(search=search, ativo=ativo)
        serializer = CorretorSerializer(corretores, many=True)
        return Response(_envelope(serializer.data))

    def post(self, request: Request) -> Response:
        serializer = CorretorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        corretor = services.corretor_create(data=serializer.validated_data)
        out = CorretorSerializer(corretor)
        return Response(_envelope(out.data), status=status.HTTP_201_CREATED)


class CorretorDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_object(self, pk: int) -> Corretor:
        try:
            return selectors.corretor_get(pk=pk)
        except Corretor.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound(detail="Corretor não encontrado.")

    def get(self, request: Request, pk: int) -> Response:
        corretor = self._get_object(pk)
        serializer = CorretorSerializer(corretor)
        return Response(_envelope(serializer.data))

    def patch(self, request: Request, pk: int) -> Response:
        corretor = self._get_object(pk)
        serializer = CorretorSerializer(corretor, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        corretor = services.corretor_update(corretor=corretor, data=serializer.validated_data)
        out = CorretorSerializer(corretor)
        return Response(_envelope(out.data))

    def delete(self, request: Request, pk: int) -> Response:
        corretor = self._get_object(pk)
        services.corretor_delete(corretor=corretor)
        return Response(status=status.HTTP_204_NO_CONTENT)
