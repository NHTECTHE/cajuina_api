from rest_framework import serializers

from apps.cotacoes.models import Cotacao
from apps.modalidades.models import Modalidade
from apps.seguradoras.models import Seguradora
from apps.segurados.models import Segurado
from apps.tomadores.models import Tomador


class CotacaoSerializer(serializers.ModelSerializer):
    # Escrita: recebe apenas os IDs das FKs.
    tomador = serializers.PrimaryKeyRelatedField(queryset=Tomador.objects.all())
    modalidade = serializers.PrimaryKeyRelatedField(queryset=Modalidade.objects.all())
    segurado = serializers.PrimaryKeyRelatedField(
        queryset=Segurado.objects.all(), required=False, allow_null=True
    )
    seguradora = serializers.PrimaryKeyRelatedField(
        queryset=Seguradora.objects.all(), required=False, allow_null=True
    )

    # Leitura: dados prontos para a lista/detalhe do frontend.
    tomador_nome = serializers.CharField(source="tomador.nome", read_only=True)
    tomador_cnpj = serializers.CharField(source="tomador.cnpj", read_only=True)
    modalidade_nome = serializers.CharField(source="modalidade.nome", read_only=True)
    segurado_nome = serializers.CharField(
        source="segurado.nome", read_only=True, default=None
    )
    segurado_cnpj = serializers.CharField(
        source="segurado.cnpj", read_only=True, default=None
    )
    seguradora_nome = serializers.CharField(
        source="seguradora.nome", read_only=True, default=None
    )
    criado_por_nome = serializers.SerializerMethodField()
    premio_seguradora = serializers.SerializerMethodField()

    def get_premio_seguradora(self, obj) -> str | None:
        """Prêmio real da seguradora escolhida, quando ela já foi cotada.

        Não sobrescreve `premio`: aquele é a nossa estimativa e continua
        valendo para cotação sem seguradora escolhida ou sem integração. Lê de
        `obj.emissoes.all()` em Python para aproveitar o prefetch da listagem
        em vez de uma consulta por linha.
        """
        if obj.seguradora_id is None:
            return None
        for emissao in obj.emissoes.all():
            if emissao.seguradora_id == obj.seguradora_id:
                return (
                    str(emissao.premio_total)
                    if emissao.premio_total is not None
                    else None
                )
        return None

    class Meta:
        model = Cotacao
        fields = (
            "id",
            "status",
            "tomador",
            "tomador_nome",
            "tomador_cnpj",
            "modalidade",
            "modalidade_nome",
            "segurado",
            "segurado_nome",
            "segurado_cnpj",
            "seguradora",
            "seguradora_nome",
            "edital",
            "data_inicio",
            "prazo_dias",
            "data_final",
            "importancia_segurada",
            "premio",
            "premio_seguradora",
            "observacoes",
            "criado_por",
            "criado_por_nome",
            "criado_em",
            "atualizado_em",
        )
        # premio é derivado da taxa do tomador: calculado no service, nunca recebido.
        read_only_fields = (
            "id",
            "status",
            "premio",
            "premio_seguradora",
            "criado_por",
            "criado_em",
            "atualizado_em",
        )

    def get_criado_por_nome(self, obj) -> str | None:
        user = obj.criado_por
        if not user:
            return None
        full_name = user.get_full_name() if hasattr(user, "get_full_name") else ""
        return full_name or getattr(user, "email", None)
