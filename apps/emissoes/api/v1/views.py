from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cotacoes.models import Cotacao
from apps.emissoes import selectors, services
from apps.emissoes.conectores.base import (
    ErroValidacaoSeguradora,
    SeguradoraIndisponivel,
)
from apps.seguradoras.models import Seguradora

from .serializers import EmissaoSeguradoraSerializer


def _envelope(data) -> dict:
    return {"data": data}


def _ler_seguradora_id(request: Request) -> int:
    """Lê e valida `seguradora` do body.

    Levanta `ValidationError` do Django, que as views já sabem transformar em
    400 — assim as duas etapas leem o campo do mesmo jeito.
    """
    bruto = request.data.get("seguradora")
    if bruto in (None, ""):
        raise ValidationError("Informe a seguradora.")
    try:
        return int(bruto)
    except (TypeError, ValueError):
        raise ValidationError("Seguradora inválida.") from None


class EmissaoEstadoView(APIView):
    """Estado persistido do wizard, uma linha por seguradora já cotada.

    Lista, e não objeto: a tela da simulação precisa saber o estado de todas as
    seguradoras de uma vez para pintar os cards.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request, pk: int) -> Response:
        if not Cotacao.objects.filter(pk=pk).exists():
            raise NotFound(detail="Cotação não encontrada.")

        emissoes = selectors.emissoes_listar_por_cotacao(cotacao_id=pk)
        return Response(
            _envelope(EmissaoSeguradoraSerializer(emissoes, many=True).data)
        )


class EmissaoCotarView(APIView):
    """Passo 1: cria ou recalcula a cotação na seguradora informada."""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request, pk: int) -> Response:
        try:
            emissao = services.emissao_cotar(
                cotacao_id=pk, seguradora_id=_ler_seguradora_id(request)
            )
        except Cotacao.DoesNotExist:
            raise NotFound(detail="Cotação não encontrada.") from None
        except Seguradora.DoesNotExist:
            raise NotFound(detail="Seguradora não encontrada.") from None
        except ValidationError as exc:
            return Response(
                {"detail": exc.messages[0]}, status=status.HTTP_400_BAD_REQUEST
            )
        except ErroValidacaoSeguradora as exc:
            # Mensagem da seguradora repassada: é acionável pelo usuário
            # ("CNPJ não cadastrado", "limite insuficiente").
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except SeguradoraIndisponivel as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response(_envelope(EmissaoSeguradoraSerializer(emissao).data))


class EmissaoMinutaView(APIView):
    """Passo 2: gera a minuta da apólice na seguradora."""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request, pk: int) -> Response:
        try:
            emissao = services.emissao_gerar_minuta(
                cotacao_id=pk,
                seguradora_id=_ler_seguradora_id(request),
                forcar_url=bool(request.data.get("forcar_url")),
            )
        except Cotacao.DoesNotExist:
            raise NotFound(detail="Cotação não encontrada.") from None
        except Seguradora.DoesNotExist:
            raise NotFound(detail="Seguradora não encontrada.") from None
        except ValidationError as exc:
            return Response(
                {"detail": exc.messages[0]}, status=status.HTTP_400_BAD_REQUEST
            )
        except ErroValidacaoSeguradora as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except SeguradoraIndisponivel as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response(_envelope(EmissaoSeguradoraSerializer(emissao).data))
