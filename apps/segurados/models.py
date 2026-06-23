from django.db import models


class Segurado(models.Model):
    cnpj = models.CharField(max_length=18, unique=True)
    natureza_juridica = models.CharField(max_length=100, blank=True, default="")
    nome = models.CharField(max_length=255)
    endereco = models.CharField(max_length=255, blank=True, default="")
    cidade = models.CharField(max_length=100, blank=True, default="")
    estado = models.CharField(max_length=2, blank=True, default="")
    bairro = models.CharField(max_length=100, blank=True, default="")
    numero = models.CharField(max_length=20, blank=True, default="")
    cep = models.CharField(max_length=10, blank=True, default="")
    complemento = models.CharField(max_length=100, blank=True, default="")
    observacoes = models.TextField(blank=True, default="")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "segurados"
        ordering = ["nome"]
        verbose_name = "Segurado"
        verbose_name_plural = "Segurados"

    def __str__(self):
        return f"{self.nome} ({self.cnpj})"
