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


class TomadorPremioAcumuladoView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_tomador(self, pk: int) -> Tomador:
        try:
            return selectors.tomador_get(pk=pk)
        except Tomador.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound(detail="Tomador não encontrado.") from None

    def get(self, request: Request, tomador_pk: int) -> Response:
        self._get_tomador(tomador_pk)
        
        from django.db.models import Sum
        from apps.apolices.models import Apolice
        from apps.seguradoras.models import Seguradora

        apolices = Apolice.objects.filter(cotacao__tomador_id=tomador_pk)
        premio_total = apolices.aggregate(total=Sum('valor_seguradora'))['total'] or 0
        
        seguradoras_qs = Seguradora.objects.filter(ativo=True).order_by('nome')
        seguradoras_list = []
        for seg in seguradoras_qs:
            total_seg = apolices.filter(seguradora=seg).aggregate(total=Sum('valor_seguradora'))['total'] or 0
            seguradoras_list.append({
                "id": seg.id,
                "nome": seg.nome,
                "total": str(total_seg)
            })
            
        return Response(_envelope({
            "premio_total": str(premio_total),
            "flex": "0.00",
            "seguradoras": seguradoras_list
        }))


class TomadorAtividadeListView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_tomador(self, pk: int) -> Tomador:
        try:
            return selectors.tomador_get(pk=pk)
        except Tomador.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound(detail="Tomador não encontrado.") from None

    def get(self, request: Request, tomador_pk: int) -> Response:
        tomador = self._get_tomador(tomador_pk)

        from apps.atividades.models import Atividade
        from apps.tomadores.models import TomadorSeguradora
        from apps.atividades.serializers import AtividadeSerializer
        from django.db.models import Q
        from django.utils.timezone import localtime
        
        # Get all TomadorSeguradora IDs for this tomador
        ts_ids = TomadorSeguradora.objects.filter(tomador_id=tomador_pk).values_list('id', flat=True)
        
        # Query activities
        atividades = Atividade.objects.filter(
            Q(entidade="Tomador", object_id=tomador_pk) |
            Q(entidade="Tomador", item=tomador.nome) | # Fallback for old logs
            Q(entidade="TomadorSeguradora", object_id__in=ts_ids) |
            Q(entidade="TomadorSeguradora", item__startswith=f"{tomador.nome} —") # Fallback for old logs
        ).order_by('-criado_em')
        
        # Format the response exactly like the mockup
        # Example mockup: { data: "05/03/2026", hora: "10:06", situacao: "Alterar Taxas", usuario: "ytallo" }
        formatted_list = []
        for a in atividades:
            situacao = a.acao
            if a.entidade == "Tomador":
                if a.acao == "CRIAÇÃO":
                    situacao = "Criação do Cadastro"
                elif a.acao == "ATUALIZAÇÃO":
                    situacao = "Atualizar Dados"
            elif a.entidade == "TomadorSeguradora":
                if a.acao == "CRIAÇÃO" or a.acao == "ATUALIZAÇÃO":
                    # Extrair o nome da seguradora do item. Ex: "Tomador — Seguradora: 5%"
                    parts = a.item.split(" — ")
                    seg_name = parts[1].split(":")[0] if len(parts) > 1 else ""
                    situacao = f"Atualização de Taxas - {seg_name}" if seg_name else "Atualização de Taxas"

            criado_em_local = localtime(a.criado_em)
            formatted_list.append({
                "id": a.id,
                "data": criado_em_local.strftime("%d/%m/%Y"),
                "hora": criado_em_local.strftime("%H:%M"),
                "situacao": situacao,
                "usuario": a.usuario_nome or "Sistema",
                "detalhes": a.detalhes
            })
            
        # Paginating the list for standard DRF/Next.js table compatibility
        page = int(request.query_params.get("page", 1))
        page_size = 10
        start = (page - 1) * page_size
        end = start + page_size
        paginated_list = formatted_list[start:end]

        return Response({
            "count": len(formatted_list),
            "next": f"?page={page + 1}" if end < len(formatted_list) else None,
            "previous": f"?page={page - 1}" if page > 1 else None,
            "results": paginated_list
        })
