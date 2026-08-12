from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.atividades.services import atividade_create
from apps.cotacoes import selectors, services
from apps.cotacoes.models import Cotacao
from shared.emails import EnvioEmailError, enviar_email
from shared.permissions import PodeEnviarComunicacao
from shared.serializers import EnvioEmailSerializer

from .serializers import CotacaoSerializer


def _envelope(data) -> dict:
    return {"data": data}


class CotacaoListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        search = request.query_params.get("search", "")
        status_param = request.query_params.get("status", "")
        cotacoes = selectors.cotacao_list(search=search, status=status_param)
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
            raise NotFound(detail="Cotação não encontrada.") from None


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
        cotacao = services.cotacao_update(
            cotacao=cotacao, data=serializer.validated_data
        )
        out = CotacaoSerializer(cotacao)
        return Response(_envelope(out.data))

    def delete(self, request: Request, pk: int) -> Response:
        cotacao = self._get_object(pk)
        services.cotacao_delete(cotacao=cotacao)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CotacaoEmailPreviewView(_CotacaoObjectMixin, APIView):
    """Mostra exatamente o que será enviado, montado pelo servidor."""

    permission_classes = [IsAuthenticated, PodeEnviarComunicacao]

    def get(self, request: Request, pk: int) -> Response:
        cotacao = self._get_object(pk)
        serializer = EnvioEmailSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        email = services.cotacao_montar_email(
            cotacao=cotacao,
            observacao=serializer.validated_data.get("observacao", ""),
        )
        return Response(_envelope(email))


class CotacaoEnviarEmailView(_CotacaoObjectMixin, APIView):
    permission_classes = [IsAuthenticated, PodeEnviarComunicacao]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "envio-email"

    def post(self, request: Request, pk: int) -> Response:
        cotacao = self._get_object(pk)
        serializer = EnvioEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = services.cotacao_montar_email(
            cotacao=cotacao,
            observacao=serializer.validated_data.get("observacao", ""),
        )
        if not email["destinatario"]:
            return Response(
                {"detail": "O tomador desta cotação não tem e-mail cadastrado."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            enviar_email(**email)
        except EnvioEmailError:
            return Response(
                {"detail": "Não foi possível enviar o e-mail. Tente novamente."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        atividade_create(
            usuario=request.user,
            acao="ENVIO",
            entidade="Cotação",
            object_id=cotacao.pk,
            item=cotacao.tomador.nome,
            detalhes=f"E-mail de cotação enviado para {email['destinatario']}.",
        )
        return Response({"detail": "E-mail enviado com sucesso."})
