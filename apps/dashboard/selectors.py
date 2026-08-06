"""Agregações de leitura da dashboard.

Este app não tem models próprios: ele só cruza apolices, cotacoes, tomadores e
seguradoras. Toda a lógica de recorte por período mora aqui para não se
espalhar (e divergir) pelos apps de domínio.
"""
import calendar
from datetime import date
from decimal import Decimal

from django.db.models import DecimalField, ExpressionWrapper, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.apolices.models import Apolice
from apps.cotacoes.models import Cotacao
from apps.seguradoras.models import Seguradora
from apps.tomadores.models import Tomador

PERIODOS_VALIDOS = ("dia", "mes", "ano")
PERIODO_PADRAO = "mes"
ZERO = Decimal("0.00")


def normalizar_periodo(periodo: str) -> str:
    """Qualquer coisa fora de dia/mes/ano vira 'mes'."""
    return periodo if periodo in PERIODOS_VALIDOS else PERIODO_PADRAO


def periodo_range(periodo: str, hoje: date | None = None) -> tuple[date, date]:
    """Devolve (inicio, fim) inclusivos para o período pedido."""
    hoje = hoje or timezone.localdate()
    periodo = normalizar_periodo(periodo)

    if periodo == "dia":
        return hoje, hoje

    if periodo == "ano":
        return date(hoje.year, 1, 1), date(hoje.year, 12, 31)

    ultimo_dia = calendar.monthrange(hoje.year, hoje.month)[1]
    return date(hoje.year, hoje.month, 1), date(hoje.year, hoje.month, ultimo_dia)


def periodo_rotulo(periodo: str, hoje: date | None = None) -> str:
    """Texto que vai nos subtítulos dos cards."""
    hoje = hoje or timezone.localdate()
    periodo = normalizar_periodo(periodo)

    if periodo == "dia":
        return hoje.strftime("%d/%m/%Y")
    if periodo == "ano":
        return hoje.strftime("%Y")
    return hoje.strftime("%m/%Y")


def resumo(*, periodo: str, hoje: date | None = None) -> dict:
    """Cards do topo e contagem de cotações, recortados pelo período."""
    hoje = hoje or timezone.localdate()
    periodo = normalizar_periodo(periodo)
    inicio, fim = periodo_range(periodo, hoje=hoje)

    apolices_periodo = Apolice.objects.filter(criado_em__date__range=(inicio, fim))
    producao = apolices_periodo.aggregate(total=Sum("cotacao__premio"))["total"] or ZERO

    cotacoes_periodo = Cotacao.objects.filter(criado_em__date__range=(inicio, fim))

    return {
        "producao": producao,
        "apolices": apolices_periodo.count(),
        "tomadores": {
            "periodo": Tomador.objects.filter(criado_em__date__range=(inicio, fim)).count(),
            "total": Tomador.objects.count(),
        },
        "cotacoes": {
            "iniciadas": cotacoes_periodo.filter(status=Cotacao.STATUS_INICIADO).count(),
            "aprovadas": cotacoes_periodo.filter(status=Cotacao.STATUS_APROVADO).count(),
            "emitidas": cotacoes_periodo.filter(status=Cotacao.STATUS_EMITIDO).count(),
        },
        "periodo": {
            "tipo": periodo,
            "inicio": inicio,
            "fim": fim,
            "rotulo": periodo_rotulo(periodo, hoje),
        },
    }


def comissoes() -> dict:
    """Saldo acumulado de comissão, agrupado por status de pagamento.

    Comissão = premio da cotação x taxa_comissao da seguradora / 100.
    Prêmio ou taxa nulos contam como zero em vez de derrubar a soma.
    """
    expressao = ExpressionWrapper(
        Coalesce(F("cotacao__premio"), Value(ZERO))
        * Coalesce(F("seguradora__taxa_comissao"), Value(ZERO))
        / Value(Decimal("100")),
        output_field=DecimalField(max_digits=18, decimal_places=2),
    )

    linhas = (
        Apolice.objects.values("status_pagamento_comissao")
        .annotate(total=Sum(expressao))
        .order_by()
    )

    por_status = {
        linha["status_pagamento_comissao"]: (linha["total"] or ZERO) for linha in linhas
    }

    a_receber = por_status.get("A Receber", ZERO)
    em_atraso = por_status.get("Atrasado", ZERO)

    return {
        "a_receber": a_receber,
        "pago": por_status.get("Recebido", ZERO),
        "em_atraso": em_atraso,
        "a_pagar": a_receber + em_atraso,
    }


def premio_por_seguradora(*, ano: int | None = None) -> list[dict]:
    """Prêmio acumulado do ano por seguradora ativa, contra a meta de cada uma.

    Seguradora sem meta cadastrada devolve meta/falta nulas — a UI omite as
    barras de comparação nesse caso em vez de fingir uma meta zero.
    """
    ano = ano or timezone.localdate().year

    seguradoras = (
        Seguradora.objects.filter(ativo=True)
        .annotate(
            valor_atual=Coalesce(
                Sum(
                    "apolices__cotacao__premio",
                    filter=Q(apolices__criado_em__year=ano),
                ),
                Value(ZERO),
                output_field=DecimalField(max_digits=18, decimal_places=2),
            )
        )
        .order_by("-valor_atual", "nome")
    )

    resultado = []
    for seguradora in seguradoras:
        meta = seguradora.meta
        falta = max(ZERO, meta - seguradora.valor_atual) if meta is not None else None
        resultado.append({
            "id": seguradora.id,
            "seguradora": seguradora.nome,
            "valor_atual": seguradora.valor_atual,
            "meta": meta,
            "falta": falta,
        })

    return resultado


PAGE_SIZE_PADRAO = 10
PAGE_SIZE_MAXIMO = 100


def novos_cadastros(*, search: str = "", page: int = 1, page_size: int = PAGE_SIZE_PADRAO) -> dict:
    """Tomadores mais recentes, com busca e paginação no banco."""
    page = max(1, page)
    page_size = max(1, min(page_size, PAGE_SIZE_MAXIMO))

    qs = Tomador.objects.select_related("criado_por").order_by("-criado_em", "-id")

    if search:
        qs = qs.filter(
            Q(nome__icontains=search)
            | Q(nome_fantasia__icontains=search)
            | Q(contato__icontains=search)
            | Q(email__icontains=search)
        )

    count = qs.count()
    inicio = (page - 1) * page_size
    pagina = qs[inicio:inicio + page_size]

    results = [
        {
            "id": tomador.id,
            "nome": tomador.nome,
            "contato": tomador.contato,
            "telefone": tomador.telefone,
            "email": tomador.email,
            "criado_por": (
                (tomador.criado_por.first_name or tomador.criado_por.email)
                if tomador.criado_por
                else None
            ),
            "criado_em": tomador.criado_em,
        }
        for tomador in pagina
    ]

    return {
        "results": results,
        "count": count,
        "page": page,
        "page_size": page_size,
    }
