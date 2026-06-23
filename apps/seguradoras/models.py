from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Seguradora(models.Model):
    nome = models.CharField(max_length=255)
    valor_licitacao = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    valor_execucao = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    taxa_comissao = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    dia_vencimento = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(31)],
    )
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "seguradoras"
        ordering = ["nome"]
        verbose_name = "Seguradora"
        verbose_name_plural = "Seguradoras"

    def __str__(self):
        return self.nome
