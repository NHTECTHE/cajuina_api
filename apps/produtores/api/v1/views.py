from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from apps.produtores import selectors, services
from apps.produtores.models import Produtor
from .serializers import ProdutorSerializer


def _envelope(data) -> dict:
    return {"data": data}


class ProdutorListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        search = request.query_params.get("search", "")
        ativo = request.query_params.get("ativo", "")
        produtores = selectors.produtor_list(search=search, ativo=ativo)
        serializer = ProdutorSerializer(produtores, many=True)
        return Response(_envelope(serializer.data))

    def post(self, request: Request) -> Response:
        serializer = ProdutorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        produtor = services.produtor_create(data=serializer.validated_data)
        out = ProdutorSerializer(produtor)
        return Response(_envelope(out.data), status=status.HTTP_201_CREATED)


class ProdutorDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_object(self, pk: int) -> Produtor:
        try:
            return selectors.produtor_get(pk=pk)
        except Produtor.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound(detail="Produtor não encontrado.")

    def get(self, request: Request, pk: int) -> Response:
        produtor = self._get_object(pk)
        serializer = ProdutorSerializer(produtor)
        return Response(_envelope(serializer.data))

    def patch(self, request: Request, pk: int) -> Response:
        produtor = self._get_object(pk)
        serializer = ProdutorSerializer(produtor, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        produtor = services.produtor_update(produtor=produtor, data=serializer.validated_data)
        out = ProdutorSerializer(produtor)
        return Response(_envelope(out.data))

    def delete(self, request: Request, pk: int) -> Response:
        produtor = self._get_object(pk)
        services.produtor_delete(produtor=produtor)
        return Response(status=status.HTTP_204_NO_CONTENT)
