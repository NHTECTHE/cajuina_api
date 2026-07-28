from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tomadores import selectors, services
from apps.tomadores.models import Tomador, TomadorArquivo, TomadorSeguradora

from .serializers import (
    TomadorArquivoSerializer,
    TomadorSeguradoraBulkSerializer,
    TomadorSeguradoraSerializer,
    TomadorSerializer,
)


def _envelope(data) -> dict:
    return {"data": data}


class TomadorListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        search = request.query_params.get("search", "")
        uf = request.query_params.get("uf", "")
        tipo = request.query_params.get("tipo", "")

        tomadores = selectors.tomador_list(search=search, uf=uf, tipo=tipo)
        serializer = TomadorSerializer(tomadores, many=True)
        return Response(_envelope(serializer.data))

    def post(self, request: Request) -> Response:
        serializer = TomadorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tomador = services.tomador_create(data=serializer.validated_data)
        out = TomadorSerializer(tomador)
        return Response(_envelope(out.data), status=status.HTTP_201_CREATED)


class TomadorDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_object(self, pk: int) -> Tomador:
        try:
            return selectors.tomador_get(pk=pk)
        except Tomador.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound(detail="Tomador não encontrado.") from None

    def get(self, request: Request, pk: int) -> Response:
        tomador = self._get_object(pk)
        serializer = TomadorSerializer(tomador)
        return Response(_envelope(serializer.data))

    def patch(self, request: Request, pk: int) -> Response:
        tomador = self._get_object(pk)
        serializer = TomadorSerializer(tomador, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        tomador = services.tomador_update(tomador=tomador, data=serializer.validated_data)
        out = TomadorSerializer(tomador)
        return Response(_envelope(out.data))

    def delete(self, request: Request, pk: int) -> Response:
        tomador = self._get_object(pk)
        services.tomador_delete(tomador=tomador)
        return Response(status=status.HTTP_204_NO_CONTENT)


class TomadorArquivoListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def _get_tomador(self, tomador_pk: int) -> Tomador:
        try:
            return selectors.tomador_get(pk=tomador_pk)
        except Tomador.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound(detail="Tomador não encontrado.") from None

    def get(self, request: Request, tomador_pk: int) -> Response:
        self._get_tomador(tomador_pk)
        arquivos = selectors.tomador_arquivo_list(tomador_id=tomador_pk)
        serializer = TomadorArquivoSerializer(arquivos, many=True, context={"request": request})
        return Response(_envelope(serializer.data))

    def post(self, request: Request, tomador_pk: int) -> Response:
        tomador = self._get_tomador(tomador_pk)
        serializer = TomadorArquivoSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        arquivo = services.tomador_arquivo_create(
            tomador=tomador,
            arquivo=serializer.validated_data["arquivo"],
        )
        out = TomadorArquivoSerializer(arquivo, context={"request": request})
        return Response(_envelope(out.data), status=status.HTTP_201_CREATED)


class TomadorArquivoDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_object(self, tomador_pk: int, pk: int) -> TomadorArquivo:
        try:
            return selectors.tomador_arquivo_get(tomador_id=tomador_pk, pk=pk)
        except TomadorArquivo.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound(detail="Arquivo não encontrado.") from None

    def delete(self, request: Request, tomador_pk: int, pk: int) -> Response:
        arquivo = self._get_object(tomador_pk, pk)
        services.tomador_arquivo_delete(arquivo=arquivo)
        return Response(status=status.HTTP_204_NO_CONTENT)


class TomadorSeguradoraListView(APIView):
    """Condições comerciais do tomador em cada seguradora.

    O PUT grava várias de uma vez, que é como a tela de taxas salva. Seguradoras
    fora do payload ficam intactas.
    """

    permission_classes = [IsAuthenticated]

    def _get_tomador(self, tomador_pk: int) -> Tomador:
        try:
            return selectors.tomador_get(pk=tomador_pk)
        except Tomador.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound(detail="Tomador não encontrado.") from None

    def get(self, request: Request, tomador_pk: int) -> Response:
        self._get_tomador(tomador_pk)

        if request.query_params.get("aptas") == "true":
            vinculos = selectors.tomador_seguradora_aptas(tomador_id=tomador_pk)
        else:
            vinculos = selectors.tomador_seguradora_list(tomador_id=tomador_pk)

        serializer = TomadorSeguradoraSerializer(vinculos, many=True)
        return Response(_envelope(serializer.data))

    def put(self, request: Request, tomador_pk: int) -> Response:
        tomador = self._get_tomador(tomador_pk)
        serializer = TomadorSeguradoraBulkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        vinculos = services.tomador_seguradora_bulk_upsert(
            tomador=tomador,
            itens=serializer.validated_data["itens"],
        )
        out = TomadorSeguradoraSerializer(vinculos, many=True)
        return Response(_envelope(out.data))


class TomadorSeguradoraDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_tomador(self, tomador_pk: int) -> Tomador:
        try:
            return selectors.tomador_get(pk=tomador_pk)
        except Tomador.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound(detail="Tomador não encontrado.") from None

    def _get_object(self, tomador_pk: int, seguradora_pk: int) -> TomadorSeguradora:
        try:
            return selectors.tomador_seguradora_get(
                tomador_id=tomador_pk, seguradora_id=seguradora_pk
            )
        except TomadorSeguradora.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound(detail="Seguradora não vinculada a este tomador.") from None

    def get(self, request: Request, tomador_pk: int, seguradora_pk: int) -> Response:
        vinculo = self._get_object(tomador_pk, seguradora_pk)
        serializer = TomadorSeguradoraSerializer(vinculo)
        return Response(_envelope(serializer.data))

    def put(self, request: Request, tomador_pk: int, seguradora_pk: int) -> Response:
        """Define as condições desta seguradora, criando o vínculo se não existir."""
        tomador = self._get_tomador(tomador_pk)

        data = {**request.data, "seguradora": seguradora_pk}
        serializer = TomadorSeguradoraSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        validated = dict(serializer.validated_data)
        seguradora = validated.pop("seguradora")
        vinculo = services.tomador_seguradora_upsert(
            tomador=tomador, seguradora=seguradora, data=validated
        )
        out = TomadorSeguradoraSerializer(vinculo)
        return Response(_envelope(out.data))

    def delete(self, request: Request, tomador_pk: int, seguradora_pk: int) -> Response:
        vinculo = self._get_object(tomador_pk, seguradora_pk)
        services.tomador_seguradora_delete(vinculo=vinculo)
        return Response(status=status.HTTP_204_NO_CONTENT)
