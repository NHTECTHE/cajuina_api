from django.db import models


class Produtor(models.Model):
    RECEBIMENTO_CHOICES = [
        ("lucro", "Lucro"),
        ("comissao", "Comissão"),
        ("premio", "Prêmio"),
    ]

    nome = models.CharField(max_length=255)
    corretora = models.ForeignKey(
        "corretores.Corretor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="produtores",
    )
    email = models.EmailField(blank=True, default="")
    telefone = models.CharField(max_length=20, blank=True, default="")
    recebimento = models.CharField(max_length=20, choices=RECEBIMENTO_CHOICES, blank=True, default="")
    percentual = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    meta = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    ativo = models.BooleanField(default=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "produtores"
        ordering = ["nome"]
        verbose_name = "Produtor"
        verbose_name_plural = "Produtores"

    def __str__(self):
        return self.nome
