from decimal import Decimal
from rest_framework import serializers
from apps.seguradoras.models import Seguradora


class SeguradoraSerializer(serializers.ModelSerializer):
    def validate_taxa_comissao(self, value):
        if value is not None and not (Decimal("0") <= value <= Decimal("100")):
            raise serializers.ValidationError("Taxa de comissão deve estar entre 0 e 100.")
        return value

    def validate_vencimento_dias(self, value):
        if value is not None and not (1 <= value <= 30):
            raise serializers.ValidationError("Vencimento deve estar entre 1 e 30 dias.")
        return value

    def validate_meta(self, value):
        if value is not None and value < Decimal("0"):
            raise serializers.ValidationError("Meta não pode ser negativa.")
        return value

    def validate_premio_minimo(self, value):
        if value < Decimal("0"):
            raise serializers.ValidationError("Prêmio mínimo não pode ser negativo.")
        return value

    class Meta:
        model = Seguradora
        fields = [
            "id",
            "nome",
            "logo",
            "meta",
            "premio_minimo",
            "taxa_comissao",
            "vencimento_dias",
            "ativo",
            "api_usuario",
            "api_senha",
            "api_ou_name",
            "api_source_app",
            "criado_em",
            "atualizado_em",
        ]
        read_only_fields = ["id", "criado_em", "atualizado_em"]
