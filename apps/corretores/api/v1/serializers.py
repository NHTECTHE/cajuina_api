
from rest_framework import serializers

from apps.corretores.models import Corretor


class CorretorSerializer(serializers.ModelSerializer):

    class Meta:
        model = Corretor
        fields = [
            "id",
            "cpf_cnpj",
            "nome",
            "criado_em",
            "atualizado_em",
        ]
        read_only_fields = ["id", "criado_em", "atualizado_em"]
