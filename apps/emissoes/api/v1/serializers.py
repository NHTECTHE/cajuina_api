from rest_framework import serializers

from apps.emissoes.models import EmissaoSeguradora


class EmissaoSeguradoraSerializer(serializers.ModelSerializer):
    """Estado da emissão para o wizard.

    `ultimo_request` e `ultima_resposta` ficam de fora por decisão, não por
    esquecimento: guardam o payload cru da seguradora, útil para diagnóstico e
    impróprio para o cliente. Por isso os campos são listados um a um em vez de
    `exclude` — campo novo no model não entra na resposta sem alguém decidir.
    """

    seguradora_nome = serializers.CharField(source="seguradora.nome", read_only=True)
    tem_apolice = serializers.SerializerMethodField()

    def get_tem_apolice(self, obj) -> bool:
        return hasattr(obj.cotacao, "apolice")

    class Meta:
        model = EmissaoSeguradora
        fields = [
            "id",
            "cotacao",
            "seguradora",
            "seguradora_nome",
            "integracao",
            "ambiente",
            "etapa",
            "external_id",
            "document_number",
            "premio_liquido",
            "premio_total",
            "taxa",
            "comissao_percentual",
            "comissao_valor",
            "numero_parcelas",
            "numero_max_parcelas",
            "opcoes_parcelamento",
            "tem_pendencias",
            "pendencias",
            "anexos_enviados",
            "codigo_retorno",
            "mensagem",
            "url_cotacao",
            "url_minuta",
            "tem_apolice",
            "criado_em",
            "atualizado_em",
        ]
        read_only_fields = fields
