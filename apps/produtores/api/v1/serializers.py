from decimal import Decimal
from rest_framework import serializers
from apps.produtores.models import Produtor
from apps.corretores.models import Corretor


class ProdutorSerializer(serializers.ModelSerializer):
    corretora_id = serializers.PrimaryKeyRelatedField(
        queryset=Corretor.objects.all(),
        source="corretora",
        allow_null=True,
        required=False,
    )
    corretora_nome = serializers.SerializerMethodField(read_only=True)

    def get_corretora_nome(self, obj):
        return obj.corretora.nome if obj.corretora else None

    def validate_percentual(self, value):
        if value is not None and not (Decimal("0") <= value <= Decimal("100")):
            raise serializers.ValidationError("Percentual deve estar entre 0 e 100.")
        return value

    class Meta:
        model = Produtor
        fields = [
            "id",
            "nome",
            "corretora_id",
            "corretora_nome",
            "email",
            "telefone",
            "recebimento",
            "percentual",
            "meta",
            "ativo",
            "criado_em",
            "atualizado_em",
        ]
        read_only_fields = ["id", "corretora_nome", "criado_em", "atualizado_em"]
