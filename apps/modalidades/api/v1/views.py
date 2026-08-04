from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.modalidades import selectors, services
from apps.modalidades.models import Modalidade, ModalidadeSeguradora
from apps.seguradoras.models import Seguradora

from .serializers import (
    MatrizSerializer,
    ModalidadeSeguradoraBulkSerializer,
    ModalidadeSeguradoraSerializer,
    ModalidadeSerializer,
)


def _envelope(data) -> dict:
    return {"data": data}


class ModalidadeListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        search = request.query_params.get("search", "")
        ativo = request.query_params.get("ativo", "")
        seguradora = request.query_params.get("seguradora", "")
        modalidades = selectors.modalidade_list(
            search=search, ativo=ativo, seguradora=seguradora
        )
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
            raise NotFound(detail="Modalidade não encontrada.") from None

    def get(self, request: Request, pk: int) -> Response:
        modalidade = self._get_object(pk)
        serializer = ModalidadeSerializer(modalidade)
        return Response(_envelope(serializer.data))

    def patch(self, request: Request, pk: int) -> Response:
        modalidade = self._get_object(pk)
        serializer = ModalidadeSerializer(modalidade, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        modalidade = services.modalidade_update(
            modalidade=modalidade, data=serializer.validated_data
        )
        out = ModalidadeSerializer(modalidade)
        return Response(_envelope(out.data))

    def delete(self, request: Request, pk: int) -> Response:
        modalidade = self._get_object(pk)
        try:
            services.modalidade_delete(modalidade=modalidade)
        except DjangoValidationError as exc:
            raise ValidationError(detail=exc.messages) from None
        return Response(status=status.HTTP_204_NO_CONTENT)


class ModalidadeSeguradoraListView(APIView):
    """Códigos desta modalidade em cada seguradora.

    O PUT grava várias de uma vez, que é como a tela de mapeamento salva.
    Seguradoras fora do payload ficam intactas.
    """

    permission_classes = [IsAuthenticated]

    def _get_modalidade(self, modalidade_pk: int) -> Modalidade:
        try:
            return selectors.modalidade_get(pk=modalidade_pk)
        except Modalidade.DoesNotExist:
            raise NotFound(detail="Modalidade não encontrada.") from None

    def get(self, request: Request, modalidade_pk: int) -> Response:
        self._get_modalidade(modalidade_pk)
        vinculos = selectors.modalidade_seguradora_list(modalidade_id=modalidade_pk)
        serializer = ModalidadeSeguradoraSerializer(vinculos, many=True)
        return Response(_envelope(serializer.data))

    def put(self, request: Request, modalidade_pk: int) -> Response:
        modalidade = self._get_modalidade(modalidade_pk)
        serializer = ModalidadeSeguradoraBulkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        services.modalidade_seguradora_bulk_upsert(
            modalidade=modalidade,
            itens=serializer.validated_data["itens"],
        )
        vinculos = selectors.modalidade_seguradora_list(modalidade_id=modalidade_pk)
        out = ModalidadeSeguradoraSerializer(vinculos, many=True)
        return Response(_envelope(out.data))


class ModalidadeSeguradoraDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_object(
        self, modalidade_pk: int, seguradora_pk: int
    ) -> ModalidadeSeguradora:
        try:
            return selectors.modalidade_seguradora_get(
                modalidade_id=modalidade_pk, seguradora_id=seguradora_pk
            )
        except ModalidadeSeguradora.DoesNotExist:
            raise NotFound(detail="Seguradora não mapeada nesta modalidade.") from None

    def get(self, request: Request, modalidade_pk: int, seguradora_pk: int) -> Response:
        vinculo = self._get_object(modalidade_pk, seguradora_pk)
        serializer = ModalidadeSeguradoraSerializer(vinculo)
        return Response(_envelope(serializer.data))

    def delete(
        self, request: Request, modalidade_pk: int, seguradora_pk: int
    ) -> Response:
        vinculo = self._get_object(modalidade_pk, seguradora_pk)
        services.modalidade_seguradora_delete(vinculo=vinculo)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MatrizView(APIView):
    """Matriz modalidades × seguradoras.

    Substitui a tela `/modalidade_seguradoras` do sistema antigo: linhas são
    modalidades, colunas são seguradoras, cada célula é o código. Célula vazia
    significa que a seguradora não oferece aquela modalidade.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        seguradoras = Seguradora.objects.filter(ativo=True)
        modalidades = Modalidade.objects.filter(ativo=True)

        # Uma query para todos os vínculos; monta o índice em memória para não
        # bater no banco por célula.
        vinculos = selectors.modalidade_seguradora_list().filter(ativo=True)
        indice: dict[int, dict[str, str]] = {}
        for vinculo in vinculos:
            indice.setdefault(vinculo.modalidade_id, {})[str(vinculo.seguradora_id)] = (
                vinculo.codigo_seguradora
            )

        linhas = [
            {
                "id": modalidade.id,
                "nome": modalidade.nome,
                "codigos": {
                    str(seguradora.id): indice.get(modalidade.id, {}).get(
                        str(seguradora.id), ""
                    )
                    for seguradora in seguradoras
                },
            }
            for modalidade in modalidades
        ]

        return Response(
            _envelope(
                {
                    "seguradoras": [{"id": s.id, "nome": s.nome} for s in seguradoras],
                    "modalidades": linhas,
                }
            )
        )

    def put(self, request: Request) -> Response:
        serializer = MatrizSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.matriz_salvar(linhas=serializer.validated_data["linhas"])
        return self.get(request)
