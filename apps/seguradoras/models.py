from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Seguradora(models.Model):
    INTEGRACAO_MANUAL = ""
    INTEGRACAO_JUNTO = "junto"
    INTEGRACAO_CHOICES = [
        (INTEGRACAO_MANUAL, "Sem integração (emissão manual)"),
        (INTEGRACAO_JUNTO, "Junto Seguros — API v2"),
    ]

    AMBIENTE_SANDBOX = "sandbox"
    AMBIENTE_PRODUCAO = "producao"
    AMBIENTE_CHOICES = [
        (AMBIENTE_SANDBOX, "Sandbox"),
        (AMBIENTE_PRODUCAO, "Produção"),
    ]

    nome = models.CharField(max_length=255)
    logo = models.ImageField(upload_to="seguradoras/logos/", null=True, blank=True)
    meta = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    premio_minimo = models.DecimalField(max_digits=14, decimal_places=2)
    taxa_comissao = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    vencimento_dias = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(30)],
    )
    ativo = models.BooleanField(default=True)

    # Credenciais de integração com a API externa da seguradora
    api_usuario = models.CharField(max_length=255, blank=True, default="")
    api_senha = models.CharField(max_length=255, blank=True, default="")
    api_ou_name = models.CharField(
        max_length=255, blank=True, default="", verbose_name="OUName"
    )
    api_source_app = models.CharField(
        max_length=255, blank=True, default="", verbose_name="SourceApp"
    )

    # Credenciais da API v2. As quatro acima são da v1 da Junto (usuário/senha) e
    # não servem aqui: a v2 autentica com um par clientId/clientSecret emitido pela
    # seguradora. Elas continuam existindo até a migration de remoção, em PR próprio.
    integracao = models.CharField(
        max_length=30,
        choices=INTEGRACAO_CHOICES,
        blank=True,
        default=INTEGRACAO_MANUAL,
        help_text="Vazio = emissão manual. Preenchido = qual conector responde por esta seguradora.",
    )
    api_client_id = models.CharField(max_length=255, blank=True, default="")
    api_client_secret = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Segredo da API. Nunca sai em resposta de GET.",
    )
    api_ambiente = models.CharField(
        max_length=10,
        choices=AMBIENTE_CHOICES,
        default=AMBIENTE_SANDBOX,
        help_text="Um id gerado no sandbox não existe em produção; trocar isto invalida emissões em andamento.",
    )

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "seguradoras"
        ordering = ["nome"]
        verbose_name = "Seguradora"
        verbose_name_plural = "Seguradoras"

    def __str__(self):
        return self.nome
