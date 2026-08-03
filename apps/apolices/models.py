from django.conf import settings
from django.db import models

from apps.cotacoes.models import Cotacao
from apps.seguradoras.models import Seguradora


class Apolice(models.Model):
    cotacao = models.OneToOneField(
        Cotacao,
        on_delete=models.PROTECT,
        related_name="apolice",
    )
    seguradora = models.ForeignKey(
        Seguradora,
        on_delete=models.PROTECT,
        related_name="apolices",
    )

    numero_apolice = models.CharField(max_length=100)
    valor_seguradora = models.DecimalField(max_digits=14, decimal_places=2)
    vencimento_boleto = models.DateField(null=True, blank=True)

    observacoes = models.TextField(blank=True, default="")
    arquivo_proposta = models.FileField(
        upload_to="apolices/propostas/%Y/%m/", null=True, blank=True
    )

    STATUS_PREMIO_CHOICES = [
        ("Pendente", "Pendente"),
        ("Pago", "Pago"),
        ("Atrasado", "Atrasado"),
    ]
    status_pagamento_premio = models.CharField(
        max_length=20, choices=STATUS_PREMIO_CHOICES, default="Pendente"
    )

    STATUS_COMISSAO_CHOICES = [
        ("A Receber", "A Receber"),
        ("Recebido", "Recebido"),
        ("Atrasado", "Atrasado"),
    ]
    status_pagamento_comissao = models.CharField(
        max_length=20, choices=STATUS_COMISSAO_CHOICES, default="A Receber"
    )

    arquivo_apolice = models.FileField(
        upload_to="apolices/apolices/%Y/%m/", null=True, blank=True
    )
    arquivo_boleto = models.FileField(
        upload_to="apolices/boletos/%Y/%m/", null=True, blank=True
    )

    emitido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="apolices",
        null=True,
        blank=True,
    )

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "apolices"
        ordering = ["-id"]
        verbose_name = "Apólice"
        verbose_name_plural = "Apólices"

    def __str__(self):
        return f"Apólice {self.numero_apolice} — Cotação #{self.cotacao_id}"
