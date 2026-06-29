from django.db import models
from django.conf import settings

class Atividade(models.Model):
    ACAO_CHOICES = [
        ('LOGIN', 'Login'),
        ('CRIAÇÃO', 'Criação'),
        ('ATUALIZAÇÃO', 'Atualização'),
        ('EXCLUSÃO', 'Exclusão'),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='atividades'
    )
    usuario_nome = models.CharField(max_length=255, blank=True, default="")
    usuario_username = models.CharField(max_length=150, blank=True, default="")
    acao = models.CharField(max_length=20, choices=ACAO_CHOICES)
    entidade = models.CharField(max_length=100)
    item = models.CharField(max_length=255)
    detalhes = models.TextField(blank=True, default="")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "atividades"
        ordering = ["-criado_em"]
        verbose_name = "Atividade"
        verbose_name_plural = "Atividades"

    def __str__(self):
        return f"{self.usuario_nome} — {self.acao} — {self.entidade}"
