from django.db import models


class Corretor(models.Model):

    cpf_cnpj = models.CharField(max_length=18, unique=True)
    nome = models.CharField(max_length=255)


    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "corretores"
        ordering = ["nome"]
        verbose_name = "Corretor"
        verbose_name_plural = "Corretores"

    def __str__(self):
        return f"{self.nome} ({self.cpf_cnpj})"
