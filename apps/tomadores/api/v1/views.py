import logging
import re
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone
from django.utils.timezone import localdate, localtime
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.apolices.models import Apolice
from apps.atividades.models import Atividade
from apps.atividades.services import atividade_create
from apps.emissoes.conectores.base import (
    ErroSeguradora,
    SeguradoraIndisponivel,
)
from apps.emissoes.conectores.registry import get_conector
from apps.seguradoras.models import Seguradora
from apps.tomadores import selectors, services
from apps.tomadores.models import Tomador, TomadorArquivo, TomadorSeguradora

from .serializers import (
    TomadorArquivoSerializer,
    TomadorSeguradoraBulkSerializer,
    TomadorSeguradoraSerializer,
    TomadorSerializer,
)

logger = logging.getLogger(__name__)

ZERO = Decimal("0.00")

# Prefixo usado para achar a solicitação recente no histórico. Fica numa constante
# porque a busca por `detalhes__startswith` quebra calada se o texto divergir.
_DETALHE_SOLICITACAO = "Cadastro solicitado na"


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


class _JuntoViewBase(APIView):
    """Pré-condições e tradução de erro comuns às três views da Junto."""

    permission_classes = [IsAuthenticated]

    def _preparar(self, tomador_pk: int, seguradora_pk: int, acao: str):
        """Valida antes de gastar uma chamada de rede.

        Devolve `(tomador, seguradora, None)` ou `(None, None, Response)` com o
        erro já montado no envelope do projeto.
        """
        tomador = _get_tomador_or_404(tomador_pk)
        try:
            seguradora = Seguradora.objects.get(pk=seguradora_pk)
        except Seguradora.DoesNotExist:
            raise NotFound(detail="Seguradora não encontrada.") from None

        if not (seguradora.integracao or "").strip():
            return None, None, self._erro(
                f"Esta seguradora não tem {acao} integrada.",
                status.HTTP_400_BAD_REQUEST,
            )

        if len(re.sub(r"\D", "", tomador.cnpj or "")) != 14:
            return None, None, self._erro(
                "CNPJ inválido.", status.HTTP_400_BAD_REQUEST
            )

        return tomador, seguradora, None

    @staticmethod
    def _erro(mensagem: str, codigo: int) -> Response:
        return Response(_envelope({"error": mensagem}), status=codigo)

    def _traduzir_erro(self, exc: ErroSeguradora) -> Response:
        """`SeguradoraIndisponivel` é 502; recusa de negócio é 400.

        A distinção importa: 400 pede correção ao usuário, 502 pede que ele tente
        de novo. Colapsar os dois foi o que fazia falha de credencial aparecer na
        tela como "tomador sem cadastro".
        """
        if isinstance(exc, SeguradoraIndisponivel):
            return self._erro(str(exc), status.HTTP_502_BAD_GATEWAY)
        return self._erro(str(exc), status.HTTP_400_BAD_REQUEST)


class TomadorSeguradoraJuntoVerificar(_JuntoViewBase):
    """Verifica o cadastro do tomador na Junto.

    Não cadastra: apenas atualiza o status do vínculo e salva a data da última
    verificação e a validade do cadastro.
    """

    def post(self, request: Request, tomador_pk: int, seguradora_pk: int) -> Response:
        tomador, seguradora, erro = self._preparar(
            tomador_pk, seguradora_pk, "verificação automática de cadastro"
        )
        if erro is not None:
            return erro

        try:
            info = get_conector(seguradora).consultar_tomador(cnpj=tomador.cnpj)
        except ErroSeguradora as e:
            return self._traduzir_erro(e)

        agora = timezone.now()
        hoje = localdate()
        validade = info.valido_ate if info else None

        with transaction.atomic():
            vinculo, _criado = TomadorSeguradora.objects.select_for_update().get_or_create(
                tomador=tomador, seguradora=seguradora
            )
            vinculo.junto_data_ultima_verificacao = agora
            vinculo.junto_validade_cadastro = validade
            # Cadastro vencido conta como sem cadastro: o POST de cadastro renova.
            vinculo.status = (
                TomadorSeguradora.Status.CADASTRO_OK
                if validade and validade >= hoje
                else TomadorSeguradora.Status.SEM_CADASTRO
            )
            vinculo.save(
                update_fields=[
                    "status",
                    "junto_data_ultima_verificacao",
                    "junto_validade_cadastro",
                    "atualizado_em",
                ]
            )

        serializer = TomadorSeguradoraSerializer(vinculo)
        return Response(_envelope(serializer.data))


class TomadorSeguradoraJuntoSolicitar(_JuntoViewBase):
    """Solicita o cadastro do tomador na Junto e registra atividade.

    Devolve `pendente` na hora: a Junto leva de 8 a 10 segundos em média e às
    vezes muito mais. Esperar aqui prenderia um worker do gunicorn por requisição
    e estouraria o `proxy_read_timeout` do nginx. Quem confirma é o botão
    "Verificar cadastro".
    """

    # Janela curta só para o duplo clique e o retry impaciente. Não é trava
    # permanente: se a primeira tentativa falhar, o usuário precisa poder repetir.
    JANELA_ANTIDUPLICIDADE = timedelta(minutes=5)

    def post(self, request: Request, tomador_pk: int, seguradora_pk: int) -> Response:
        tomador, seguradora, erro = self._preparar(
            tomador_pk, seguradora_pk, "cadastro automático"
        )
        if erro is not None:
            return erro

        # Prevenir solicitações duplicadas imediatas: verificar se já existe
        # uma atividade de Criação para este vínculo.
        from apps.atividades.services import atividade_create

        # Evita recadastrar quem já está com Cadastro OK, mas permite tentar novamente se deu erro antes
        if vinculo.status == TomadorSeguradora.Status.CADASTRO_OK:
            serializer = TomadorSeguradoraSerializer(vinculo)
            return Response(_envelope(serializer.data))

        # A atividade só é gravada depois do POST sair: registrar antes faria o
        # histórico afirmar uma solicitação que pode nem ter acontecido.
        atividade_create(
            usuario=request.user if request.user.is_authenticated else None,
            acao="ATUALIZAÇÃO",
            entidade="Tomador",
            object_id=tomador.id,
            item=tomador.nome,
            detalhes=f"{_DETALHE_SOLICITACAO} {seguradora.nome}",
        )

        # Preparar payload mínimo para a Junto
        dados = {
            "federalId": ''.join(filter(str.isdigit, tomador.cnpj or "")),
        }

        from django.utils import timezone

        from shared.integracoes.junto.client import JuntoAPIError, JuntoClient

        try:
            client = JuntoClient(vinculo.seguradora)
            resp = client.solicitar_cadastro_tomador(dados)
        except JuntoAPIError as e:
            return Response(_envelope({"error": str(e)}), status=status.HTTP_502_BAD_GATEWAY)

        # Na V1 a resposta tinha {"status": "processing"}, na V2 se não der erro (Exception), já consideramos que está em processamento
        processing = True
        found_imediato = False
        
        # Na V2, o POST já retorna o Tomador diretamente se der sucesso
        if isinstance(resp, dict) and resp.get("federalId"):
            found_imediato = True
            found = resp
            processing = False

        if processing:
            # Poll por alguns segundos
            import time

            found = None
            for _ in range(12):
                time.sleep(1)
                try:
                    found = client.consultar_tomador(tomador.cnpj)
                except JuntoAPIError:
                    found = None
                if found:
                    break
                    
        if found_imediato:
            pass # já temos o 'found' preenchido do retorno imediato da V2
            
        vinculo.junto_data_ultima_verificacao = timezone.now()

        if found:
            # Atualiza validade e status
            try:
                from datetime import date

                validade_str = found.get("dateExpirationRegistration") or found.get("validade")
                if validade_str:
                    vinculo.junto_validade_cadastro = date.fromisoformat(validade_str.split("T")[0])
            except Exception:
                vinculo.junto_validade_cadastro = None

            from django.utils.timezone import localdate
            hoje = localdate()
            
            # Regras de Negócio Junto Seguros V2
            serasa_status = found.get("serasaStatus") or {}
            status_id = serasa_status.get("statusId") if isinstance(serasa_status, dict) else None
            
            if status_id in (2, 4):
                # 2 = Serasa com Restrições, 4 = Bloqueado
                vinculo.status = TomadorSeguradora.Status.SEM_ACEITACAO
            elif vinculo.junto_validade_cadastro and vinculo.junto_validade_cadastro >= hoje:
                vinculo.status = TomadorSeguradora.Status.CADASTRO_OK
            elif found:
                # Na V2 (Sandbox), se retornou o tomador mas não tem data de validade, consideramos Cadastro OK para testes
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
        return Response(
            _envelope({**serializer.data, "pendente": True}),
            status=status.HTTP_202_ACCEPTED,
        )


class TomadorSeguradoraJuntoConsultarTaxa(_JuntoViewBase):
    """Consulta a taxa do tomador na Junto e registra no histórico.

    Não grava a taxa nem cria vínculo: quem persiste continua sendo o
    `PUT /api/v1/tomadores/{id}/seguradoras/` do "Salvar Taxas", para que exista
    um caminho de escrita só.
    """

    def post(self, request: Request, tomador_pk: int, seguradora_pk: int) -> Response:
        tomador, seguradora, erro = self._preparar(
            tomador_pk, seguradora_pk, "consulta de taxa"
        )
        if erro is not None:
            return erro

        try:
            taxa = get_conector(seguradora).consultar_taxa_tomador(cnpj=tomador.cnpj)
        except ErroSeguradora as e:
            return self._traduzir_erro(e)

        if taxa is None:
            return self._erro(
                f"Este tomador não tem cadastro/limite na {seguradora.nome}.",
                status.HTTP_404_NOT_FOUND,
            )

        if taxa.taxa >= Decimal("1000") or -taxa.taxa.as_tuple().exponent > 6:
            # Arredondar calado é o que a precisão de 6 casas existe para evitar.
            return self._erro(
                f"Taxa fora da faixa suportada: {taxa.taxa}.",
                status.HTTP_400_BAD_REQUEST,
            )

        resultado = {
            "taxa": f"{taxa.taxa:f}",
            "modalidade_id": str(taxa.modalidade_id),
            "modalidade_descricao": taxa.modalidade_descricao,
            "limite_disponivel": f"{taxa.limite_disponivel:f}",
            "data_consulta": timezone.localtime().isoformat(),
            "origem": "junto",
        }

        atividade_create(
            usuario=request.user if request.user.is_authenticated else None,
            acao="ATUALIZAÇÃO",
            entidade="Tomador",
            object_id=tomador.id,
            item=tomador.nome,
            detalhes=(
                f"Taxa {taxa.taxa}% consultada na {seguradora.nome} — "
                f"modalidade {taxa.modalidade_id} ({taxa.modalidade_descricao})"
            ),
        )

        return Response(_envelope(resultado))
