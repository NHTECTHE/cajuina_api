from django.conf import settings
from django.db import models


class Notificacao(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notificacoes"
    )
    titulo = models.CharField(max_length=255)
    mensagem = models.TextField()
    status_badge = models.CharField(max_length=50, blank=True, null=True)
    lida = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notificacoes"
        ordering = ["-criado_em"]
        verbose_name = "Notificação"
        verbose_name_plural = "Notificações"

    def __str__(self):
        return f"Para: {self.usuario.email} - {self.titulo}"
