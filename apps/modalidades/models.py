from django.db import models

class Modalidade(models.Model):
    nome = models.CharField(max_length=255)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "modalidades"
        ordering = ["nome"]
        verbose_name = "Modalidade"
        verbose_name_plural = "Modalidades"

    def __str__(self):
        return self.nome
