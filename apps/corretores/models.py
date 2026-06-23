from django.db import models


class Corretor(models.Model):
    RECEBIMENTO_CHOICES = [
        ("pix", "PIX"),
        ("ted", "TED"),
        ("doc", "DOC"),
        ("boleto", "Boleto"),
    ]

    cpf_cnpj = models.CharField(max_length=18, unique=True)
    nome = models.CharField(max_length=255)
    recebimento = models.CharField(max_length=20, choices=RECEBIMENTO_CHOICES, blank=True, default="")
    percentual = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    banco = models.CharField(max_length=100, blank=True, default="")
    agencia = models.CharField(max_length=20, blank=True, default="")
    conta = models.CharField(max_length=30, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    telefone = models.CharField(max_length=20, blank=True, default="")
    url_saida = models.URLField(max_length=500, blank=True, default="")
    ativo = models.BooleanField(default=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "corretores"
        ordering = ["nome"]
        verbose_name = "Corretor"
        verbose_name_plural = "Corretores"

    def __str__(self):
        return f"{self.nome} ({self.cpf_cnpj})"
