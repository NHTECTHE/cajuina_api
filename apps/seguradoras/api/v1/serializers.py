from decimal import Decimal
from rest_framework import serializers
from apps.seguradoras.models import Seguradora


class SeguradoraSerializer(serializers.ModelSerializer):
    def validate_taxa_comissao(self, value):
        if value is not None and not (Decimal("0") <= value <= Decimal("100")):
            raise serializers.ValidationError("Taxa de comissão deve estar entre 0 e 100.")
        return value

    def validate_dia_vencimento(self, value):
        if value is not None and not (1 <= value <= 31):
            raise serializers.ValidationError("Dia de vencimento deve estar entre 1 e 31.")
        return value

    def validate_valor_licitacao(self, value):
        if value is not None and value < Decimal("0"):
            raise serializers.ValidationError("Valor de licitação não pode ser negativo.")
        return value

    def validate_valor_execucao(self, value):
        if value is not None and value < Decimal("0"):
            raise serializers.ValidationError("Valor de execução não pode ser negativo.")
        return value

    class Meta:
        model = Seguradora
        fields = [
            "id",
            "nome",
            "valor_licitacao",
            "valor_execucao",
            "taxa_comissao",
            "dia_vencimento",
            "ativo",
            "criado_em",
            "atualizado_em",
        ]
        read_only_fields = ["id", "criado_em", "atualizado_em"]
