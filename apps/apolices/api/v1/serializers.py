from rest_framework import serializers

from apps.apolices.models import Apolice
from apps.seguradoras.models import Seguradora


class ApoliceSerializer(serializers.ModelSerializer):
    seguradora = serializers.PrimaryKeyRelatedField(queryset=Seguradora.objects.all())

    seguradora_nome = serializers.CharField(source="seguradora.nome", read_only=True)
    tomador_nome = serializers.CharField(source="cotacao.tomador.nome", read_only=True)
    tomador_cnpj = serializers.CharField(source="cotacao.tomador.cnpj", read_only=True)
    modalidade_nome = serializers.CharField(source="cotacao.modalidade.nome", read_only=True)
    segurado_nome = serializers.CharField(source="cotacao.segurado.nome", read_only=True, allow_null=True)
    edital = serializers.CharField(source="cotacao.edital", read_only=True, allow_null=True)
    data_inicio = serializers.DateField(source="cotacao.data_inicio", read_only=True, allow_null=True)
    data_final = serializers.DateField(source="cotacao.data_final", read_only=True, allow_null=True)
    prazo_dias = serializers.IntegerField(source="cotacao.prazo_dias", read_only=True, allow_null=True)
    importancia_segurada = serializers.DecimalField(source="cotacao.importancia_segurada", max_digits=14, decimal_places=2, read_only=True, allow_null=True)
    emitido_por_nome = serializers.SerializerMethodField()

    class Meta:
        model = Apolice
        fields = (
            "id",
            "cotacao",
            "tomador_nome",
            "tomador_cnpj",
            "modalidade_nome",
            "segurado_nome",
            "edital",
            "data_inicio",
            "data_final",
            "prazo_dias",
            "importancia_segurada",
            "seguradora",
            "seguradora_nome",
            "numero_apolice",
            "valor_seguradora",
            "vencimento_boleto",
            "arquivo_apolice",
            "arquivo_boleto",
            "arquivo_proposta",
            "observacoes",
            "status_pagamento_premio",
            "status_pagamento_comissao",
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
        return full_name or getattr(user, "email", None)
