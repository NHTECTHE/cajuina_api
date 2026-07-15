from rest_framework import serializers

from apps.apolices.models import Apolice
from apps.seguradoras.models import Seguradora


class ApoliceSerializer(serializers.ModelSerializer):
    seguradora = serializers.PrimaryKeyRelatedField(queryset=Seguradora.objects.all())

    seguradora_nome = serializers.CharField(source="seguradora.nome", read_only=True)
    tomador_nome = serializers.CharField(source="cotacao.tomador.nome", read_only=True)
    tomador_cnpj = serializers.CharField(source="cotacao.tomador.cnpj", read_only=True)
    modalidade_nome = serializers.CharField(source="cotacao.modalidade.nome", read_only=True)
    emitido_por_nome = serializers.SerializerMethodField()

    class Meta:
        model = Apolice
        fields = (
            "id",
            "cotacao",
            "tomador_nome",
            "tomador_cnpj",
            "modalidade_nome",
            "seguradora",
            "seguradora_nome",
            "numero_apolice",
            "valor_seguradora",
            "arquivo_apolice",
            "arquivo_boleto",
            "emitido_por",
            "emitido_por_nome",
            "criado_em",
            "atualizado_em",
        )
        read_only_fields = ("id", "cotacao", "emitido_por", "criado_em", "atualizado_em")

    def get_emitido_por_nome(self, obj) -> str | None:
        user = obj.emitido_por
        if not user:
            return None
        full_name = user.get_full_name() if hasattr(user, "get_full_name") else ""
        return full_name or getattr(user, "username", None) or getattr(user, "email", None)
