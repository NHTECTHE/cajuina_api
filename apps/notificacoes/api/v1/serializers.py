from rest_framework import serializers
from apps.notificacoes.models import Notificacao

class NotificacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notificacao
        fields = ["id", "titulo", "mensagem", "status_badge", "lida", "criado_em"]
        read_only_fields = fields
