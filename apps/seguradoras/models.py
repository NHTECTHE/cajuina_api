from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Seguradora(models.Model):
    nome = models.CharField(max_length=255)
    logo = models.ImageField(upload_to="seguradoras/logos/", null=True, blank=True)
    meta = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    premio_minimo = models.DecimalField(max_digits=14, decimal_places=2)
    taxa_comissao = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    vencimento_dias = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(30)],
    )
    ativo = models.BooleanField(default=True)

    # Credenciais de integração com a API externa da seguradora
    api_usuario = models.CharField(max_length=255, blank=True, default="")
    api_senha = models.CharField(max_length=255, blank=True, default="")
    api_ou_name = models.CharField(max_length=255, blank=True, default="", verbose_name="OUName")
    api_source_app = models.CharField(max_length=255, blank=True, default="", verbose_name="SourceApp")

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "seguradoras"
        ordering = ["nome"]
        verbose_name = "Seguradora"
        verbose_name_plural = "Seguradoras"

    def __str__(self):
        return self.nome
