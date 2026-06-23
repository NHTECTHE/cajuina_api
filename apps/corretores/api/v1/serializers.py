from decimal import Decimal
from rest_framework import serializers
from apps.corretores.models import Corretor


class CorretorSerializer(serializers.ModelSerializer):
    def validate_percentual(self, value):
        if value is not None and not (Decimal("0") <= value <= Decimal("100")):
            raise serializers.ValidationError("Percentual deve estar entre 0 e 100.")
        return value

    class Meta:
        model = Corretor
        fields = [
            "id",
            "cpf_cnpj",
            "nome",
            "recebimento",
            "percentual",
            "banco",
            "agencia",
            "conta",
            "email",
            "telefone",
            "url_saida",
            "ativo",
            "criado_em",
            "atualizado_em",
        ]
        read_only_fields = ["id", "criado_em", "atualizado_em"]
