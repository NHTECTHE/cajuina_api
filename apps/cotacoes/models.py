from django.conf import settings
from django.db import models

from apps.modalidades.models import Modalidade
from apps.segurados.models import Segurado
from apps.tomadores.models import Tomador


class Cotacao(models.Model):
    STATUS_INICIADO = "Iniciado"
    STATUS_APROVADO = "Aprovado"
    STATUS_CHOICES = [
        (STATUS_INICIADO, "Iniciado"),
        (STATUS_APROVADO, "Aprovado"),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_INICIADO,
    )

    tomador = models.ForeignKey(
        Tomador,
        on_delete=models.PROTECT,
        related_name="cotacoes",
    )
    modalidade = models.ForeignKey(
        Modalidade,
        on_delete=models.PROTECT,
        related_name="cotacoes",
    )
    segurado = models.ForeignKey(
        Segurado,
        on_delete=models.PROTECT,
        related_name="cotacoes",
        null=True,
        blank=True,
    )

    edital = models.CharField(max_length=255, blank=True, default="")
    data_inicio = models.DateField(null=True, blank=True)
    prazo_dias = models.PositiveIntegerField(null=True, blank=True)
    data_final = models.DateField(null=True, blank=True)
    importancia_segurada = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
    )
    observacoes = models.TextField(blank=True, default="")

    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="cotacoes",
        null=True,
        blank=True,
    )

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cotacoes"
        ordering = ["-id"]
        verbose_name = "Cotação"
        verbose_name_plural = "Cotações"

    def __str__(self):
        return f"Cotação #{self.pk} — {self.tomador.nome}"
