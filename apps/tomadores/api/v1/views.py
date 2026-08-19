from decimal import Decimal

from django.db.models import Q, Sum
from django.utils.timezone import localtime
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.apolices.models import Apolice
from apps.atividades.models import Atividade
from apps.seguradoras.models import Seguradora
from apps.tomadores import selectors, services
from apps.tomadores.models import Tomador, TomadorArquivo, TomadorSeguradora

from .serializers import (
    TomadorArquivoSerializer,
    TomadorSeguradoraBulkSerializer,
    TomadorSeguradoraSerializer,
    TomadorSerializer,
)

ZERO = Decimal("0.00")


def _envelope(data) -> dict:
    return {"data": data}


def _get_tomador_or_404(pk: int) -> Tomador:
    try:
        return selectors.tomador_get(pk=pk)
    except Tomador.DoesNotExist:
        raise NotFound(detail="Tomador não encontrado.") from None


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

        tomador = services.tomador_create(
            data=serializer.validated_data,
            criado_por=request.user if request.user.is_authenticated else None,
        )
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

        tomador = services.tomador_update(
            tomador=tomador, data=serializer.validated_data
        )
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
        serializer = TomadorArquivoSerializer(
            arquivos, many=True, context={"request": request}
        )
        return Response(_envelope(serializer.data))

    def post(self, request: Request, tomador_pk: int) -> Response:
        tomador = self._get_tomador(tomador_pk)
        serializer = TomadorArquivoSerializer(
            data=request.data, context={"request": request}
        )
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


class TomadorPremioAcumuladoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, tomador_pk: int) -> Response:
        _get_tomador_or_404(tomador_pk)

        apolices = Apolice.objects.filter(cotacao__tomador_id=tomador_pk)
        premio_total = (
            apolices.aggregate(total=Sum("valor_seguradora"))["total"] or ZERO
        )

        # Um único agregado por seguradora em vez de um `aggregate` por linha do
        # loop — o custo deixa de crescer com a quantidade de seguradoras ativas.
        totais = {
            row["seguradora_id"]: row["total"]
            for row in apolices.values("seguradora_id").annotate(
                total=Sum("valor_seguradora")
            )
        }

        seguradoras_list = [
            {
                "id": seguradora.id,
                "nome": seguradora.nome,
                "total": str(totais.get(seguradora.id) or ZERO),
            }
            for seguradora in Seguradora.objects.filter(ativo=True).order_by("nome")
        ]

        return Response(
            _envelope(
                {
                    "premio_total": str(premio_total),
                    # `flex` ainda não tem regra de cálculo definida; `null`
                    # distingue "não calculado" de um zero legítimo.
                    "flex": None,
                    "seguradoras": seguradoras_list,
                }
            )
        )


class TomadorAtividadeListView(APIView):
    permission_classes = [IsAuthenticated]

    PAGE_SIZE = 10

    SITUACAO_TOMADOR = {
        "CRIAÇÃO": "Criação do Cadastro",
        "ATUALIZAÇÃO": "Atualizar Dados",
    }

    def get(self, request: Request, tomador_pk: int) -> Response:
        _get_tomador_or_404(tomador_pk)

        ts_ids = TomadorSeguradora.objects.filter(tomador_id=tomador_pk).values_list(
            "id", flat=True
        )

        atividades = Atividade.objects.filter(
            Q(entidade="Tomador", object_id=tomador_pk)
            | Q(entidade="TomadorSeguradora", object_id__in=ts_ids)
        ).order_by("-criado_em")

        page = self._get_page(request)
        total = atividades.count()
        start = (page - 1) * self.PAGE_SIZE
        end = start + self.PAGE_SIZE

        # O slice é aplicado ao queryset (vira LIMIT/OFFSET) antes da formatação,
        # então só as linhas da página atual saem do banco.
        results = [self._formatar(atividade) for atividade in atividades[start:end]]

        return Response(
            _envelope(
                {
                    "count": total,
                    "next": f"?page={page + 1}" if end < total else None,
                    "previous": f"?page={page - 1}" if page > 1 else None,
                    "results": results,
                }
            )
        )

    def _get_page(self, request: Request) -> int:
        """Página pedida, normalizada. Entrada inválida cai para 1 em vez de 500."""
        try:
            page = int(request.query_params.get("page", 1))
        except (TypeError, ValueError):
            return 1
        return max(page, 1)

    def _situacao(self, atividade: Atividade) -> str:
        if atividade.entidade == "Tomador":
            return self.SITUACAO_TOMADOR.get(atividade.acao, atividade.acao)

        if atividade.entidade == "TomadorSeguradora" and atividade.acao in (
            "CRIAÇÃO",
            "ATUALIZAÇÃO",
        ):
            # `item` vem de TomadorSeguradora.__str__: "Tomador — Seguradora: 5.00%"
            partes = atividade.item.split(" — ")
            seguradora = partes[1].split(":")[0].strip() if len(partes) > 1 else ""
            return (
                f"Atualização de Taxas - {seguradora}"
                if seguradora
                else "Atualização de Taxas"
            )

        return atividade.acao

    def _formatar(self, atividade: Atividade) -> dict:
        criado_em = localtime(atividade.criado_em)
        return {
            "id": atividade.id,
            "data": criado_em.strftime("%d/%m/%Y"),
            "hora": criado_em.strftime("%H:%M"),
            "situacao": self._situacao(atividade),
            "usuario": atividade.usuario_nome or "Sistema",
            "detalhes": atividade.detalhes,
        }


class TomadorSeguradoraJuntoVerificar(APIView):
    """Verifica o cadastro do tomador na Junto.

    Não deve cadastrar automaticamente; apenas atualiza o status do vínculo
    e salva a data da última verificação e a validade do cadastro.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request, tomador_pk: int, seguradora_pk: int) -> Response:
        try:
            tomador = selectors.tomador_get(pk=tomador_pk)
        except Tomador.DoesNotExist:
            raise NotFound(detail="Tomador não encontrado.") from None

        # Garantir vínculo existe
        vinculo, _ = TomadorSeguradora.objects.get_or_create(
            tomador=tomador, seguradora_id=seguradora_pk
        )

        # Integração com Junto
        from shared.integracoes.junto.client import JuntoClient, JuntoAPIError
        from django.utils import timezone

        try:
            client = JuntoClient(vinculo.seguradora)
            result = client.consultar_tomador(tomador.cnpj)
        except JuntoAPIError as e:
            return Response(_envelope({"error": str(e)}), status=status.HTTP_502_BAD_GATEWAY)

        vinculo.junto_data_ultima_verificacao = timezone.now()

        if result is None:
            vinculo.status = TomadorSeguradora.Status.SEM_CADASTRO
            vinculo.junto_validade_cadastro = None
            vinculo.save(update_fields=["status", "junto_data_ultima_verificacao", "junto_validade_cadastro", "atualizado_em"])
            serializer = TomadorSeguradoraSerializer(vinculo)
            return Response(_envelope(serializer.data))

        # Se retornou dados, extrair validade (se houver) e considerar vencimento
        validade = None
        try:
            validade_str = result.get("validade")
            if validade_str:
                from datetime import date

                validade = date.fromisoformat(validade_str)
                vinculo.junto_validade_cadastro = validade
        except Exception:
            vinculo.junto_validade_cadastro = None

        # Verifica se validade está expirada
        from django.utils.timezone import localdate

        hoje = localdate()
        if vinculo.junto_validade_cadastro and vinculo.junto_validade_cadastro >= hoje:
            vinculo.status = TomadorSeguradora.Status.CADASTRO_OK
        else:
            vinculo.status = TomadorSeguradora.Status.SEM_CADASTRO

        vinculo.save(update_fields=["status", "junto_data_ultima_verificacao", "junto_validade_cadastro", "atualizado_em"])
        serializer = TomadorSeguradoraSerializer(vinculo)
        return Response(_envelope(serializer.data))


class TomadorSeguradoraJuntoSolicitar(APIView):
    """Solicita o cadastro do tomador na Junto e registra atividade.

    Evita solicitações duplicadas simultâneas e realiza polling breve para
    confirmar processamento; se ainda estiver processando, retorna pendente
    mantendo o vínculo como `sem_cadastro`.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request, tomador_pk: int, seguradora_pk: int) -> Response:
        try:
            tomador = selectors.tomador_get(pk=tomador_pk)
        except Tomador.DoesNotExist:
            raise NotFound(detail="Tomador não encontrado.") from None

        vinculo, _ = TomadorSeguradora.objects.get_or_create(
            tomador=tomador, seguradora_id=seguradora_pk
        )

        # Prevenir solicitações duplicadas imediatas: verificar se já existe
        # uma atividade de Criação para este vínculo.
        from apps.atividades.models import Atividade
        from apps.atividades.services import atividade_create

        existe_atividade = Atividade.objects.filter(
            entidade="TomadorSeguradora", object_id=vinculo.id, acao="Criação"
        ).exists()

        if existe_atividade:
            serializer = TomadorSeguradoraSerializer(vinculo)
            return Response(_envelope(serializer.data))

        # Registrar atividade de solicitação
        usuario = request.user if request.user.is_authenticated else None
        atividade_create(
            usuario=usuario,
            acao="Criação",
            entidade="TomadorSeguradora",
            object_id=vinculo.id,
            item=str(vinculo),
            detalhes="Solicitação de cadastro na Junto",
        )

        # Preparar payload mínimo para a Junto
        dados = {
            "cnpj": ''.join(filter(str.isdigit, tomador.cnpj or "")),
            "nome": tomador.nome or tomador.nome_fantasia or "",
            "email": tomador.email,
        }

        from shared.integracoes.junto.client import JuntoClient, JuntoAPIError
        from django.utils import timezone

        try:
            client = JuntoClient(vinculo.seguradora)
            resp = client.solicitar_cadastro_tomador(dados)
        except JuntoAPIError as e:
            return Response(_envelope({"error": str(e)}), status=status.HTTP_502_BAD_GATEWAY)

        # Se resposta indicar processamento, tentar consultar algumas vezes
        processing = False
        try:
            status_val = resp.get("status") if isinstance(resp, dict) else None
            if status_val and str(status_val).lower() in ("processing", "pendente"):
                processing = True
        except Exception:
            processing = False

        if processing:
            # Poll por alguns segundos
            import time

            found = None
            for _ in range(4):
                time.sleep(1)
                try:
                    found = client.consultar_tomador(tomador.cnpj)
                except JuntoAPIError:
                    found = None
                if found:
                    break

            vinculo.junto_data_ultima_verificacao = timezone.now()

            if found:
                # Atualiza validade e status
                try:
                    from datetime import date

                    validade_str = found.get("validade")
                    if validade_str:
                        vinculo.junto_validade_cadastro = date.fromisoformat(validade_str)
                except Exception:
                    vinculo.junto_validade_cadastro = None

                from django.utils.timezone import localdate

                hoje = localdate()
                if vinculo.junto_validade_cadastro and vinculo.junto_validade_cadastro >= hoje:
                    vinculo.status = TomadorSeguradora.Status.CADASTRO_OK
                else:
                    vinculo.status = TomadorSeguradora.Status.SEM_CADASTRO

                vinculo.save(update_fields=["status", "junto_data_ultima_verificacao", "junto_validade_cadastro", "atualizado_em"])
                serializer = TomadorSeguradoraSerializer(vinculo)
                return Response(_envelope(serializer.data))

            # Ainda processando: manter sem cadastro e informar pendente
            vinculo.junto_data_ultima_verificacao = timezone.now()
            vinculo.save(update_fields=["junto_data_ultima_verificacao", "atualizado_em"])
            serializer = TomadorSeguradoraSerializer(vinculo)
            return Response(_envelope({**serializer.data, "pendente": True}))

        # Se não estava em processamento (retorno imediato), tentar interpretar resposta
        vinculo.junto_data_ultima_verificacao = timezone.now()
        vinculo.save(update_fields=["junto_data_ultima_verificacao", "atualizado_em"])
        serializer = TomadorSeguradoraSerializer(vinculo)
        return Response(_envelope(serializer.data))
