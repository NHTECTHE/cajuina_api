from rest_framework import serializers
from apps.segurados.models import Segurado


class SeguradoSerializer(serializers.ModelSerializer):
    def validate_observacoes(self, value):
        if len(value) > 500:
            raise serializers.ValidationError("Observações não podem exceder 500 caracteres.")
        return value

    class Meta:
        model = Segurado
        fields = [
            "id",
            "cnpj",
            "natureza_juridica",
            "nome",
            "endereco",
            "cidade",
            "estado",
            "bairro",
            "numero",
            "cep",
            "complemento",
            "observacoes",
            "criado_em",
            "atualizado_em",
        ]
        read_only_fields = ["id", "criado_em", "atualizado_em"]
