from django.core.serializers.json import DjangoJSONEncoder
from django.db import models

from apps.cotacoes.models import Cotacao
from apps.seguradoras.models import Seguradora


class EmissaoSeguradora(models.Model):
    """Estado da emissão de uma cotação junto à seguradora integrada.

    Fica fora da `Cotacao` de propósito: o wizard é retomável e o processo é
    stateful do lado de lá (id da cotação, número do documento, pendências,
    código de retorno). Guardar isso na `Cotacao` poluiria o nosso domínio com
    vocabulário da seguradora e quebraria na segunda seguradora.

    É também o registro de idempotência, agora por par: a constraint única em
    (cotacao, seguradora) garante que uma cotação nossa vira no máximo uma
    cotação por seguradora lá dentro. Várias linhas por cotação é o desenho,
    não um efeito colateral — cotar em três seguradoras e comparar antes de
    escolher é requisito, e é o que o legado fazia em `valores_simulacao`.
    """

    ETAPA_COTADA = "cotada"
    ETAPA_MINUTA = "minuta"
    ETAPA_AGUARDANDO = "aguardando"
    ETAPA_EMITIDA = "emitida"
    ETAPA_RECUSADA = "recusada"
    ETAPA_CHOICES = [
        (ETAPA_COTADA, "Cotada"),
        (ETAPA_MINUTA, "Minuta gerada"),
        (ETAPA_AGUARDANDO, "Aguardando seguradora"),
        (ETAPA_EMITIDA, "Emitida"),
        (ETAPA_RECUSADA, "Recusada"),
    ]

    cotacao = models.ForeignKey(
        Cotacao, on_delete=models.CASCADE, related_name="emissoes"
    )
    seguradora = models.ForeignKey(
        Seguradora, on_delete=models.PROTECT, related_name="emissoes"
    )
    integracao = models.CharField(
        max_length=30,
        help_text="Cópia de Seguradora.integracao no momento em que a emissão começou.",
    )

    etapa = models.CharField(max_length=20, choices=ETAPA_CHOICES, default=ETAPA_COTADA)

    external_id = models.CharField(
        max_length=50, blank=True, default="", help_text="Id da cotação na seguradora."
    )
    document_number = models.CharField(max_length=50, blank=True, default="")

    premio_liquido = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    premio_total = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    # 6 casas: a taxa da seguradora tem mais precisão que a nossa taxa
    # comercial de 2 casas em TomadorSeguradora.
    taxa = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    comissao_percentual = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    comissao_valor = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )

    numero_parcelas = models.PositiveSmallIntegerField(null=True, blank=True)
    # Persistido, e não só devolvido na resposta do passo 1: o wizard é
    # retomável, e sem isto o front não remonta o select de parcelas depois de
    # um F5 — teria de recotar na seguradora só para redesenhar a tela.
    numero_max_parcelas = models.PositiveSmallIntegerField(null=True, blank=True)
    opcoes_parcelamento = models.JSONField(
        default=list, blank=True, encoder=DjangoJSONEncoder
    )

    tem_pendencias = models.BooleanField(default=False)
    pendencias = models.JSONField(default=list, blank=True, encoder=DjangoJSONEncoder)
    anexos_enviados = models.PositiveSmallIntegerField(default=0)

    ambiente = models.CharField(
        max_length=10,
        help_text="Congela Seguradora.api_ambiente no passo 1: um id de sandbox não existe em produção.",
    )
    dados_cotados = models.JSONField(
        default=dict,
        blank=True,
        encoder=DjangoJSONEncoder,
        help_text="Snapshot do que foi enviado. Os passos seguintes comparam com a cotação atual.",
    )

    codigo_retorno = models.CharField(max_length=20, blank=True, default="")
    mensagem = models.TextField(blank=True, default="")

    url_cotacao = models.URLField(blank=True, default="", max_length=500)
    url_minuta = models.URLField(blank=True, default="", max_length=500)

    # Payload cru, só para auditoria e diagnóstico. NUNCA serializado ao cliente.
    ultimo_request = models.JSONField(null=True, blank=True, encoder=DjangoJSONEncoder)
    ultima_resposta = models.JSONField(null=True, blank=True, encoder=DjangoJSONEncoder)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "emissoes_seguradora"
        ordering = ["-id"]
        verbose_name = "Emissão na seguradora"
        verbose_name_plural = "Emissões na seguradora"
        constraints = [
            models.UniqueConstraint(
                fields=["cotacao", "seguradora"],
                name="emissao_unica_por_cotacao_seguradora",
            )
        ]

    def __str__(self):
        return (
            f"Emissão da cotação #{self.cotacao_id} — {self.seguradora} ({self.etapa})"
        )
