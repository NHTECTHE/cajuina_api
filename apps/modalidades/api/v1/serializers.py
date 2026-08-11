from rest_framework import serializers

from apps.modalidades.models import Modalidade, ModalidadeSeguradora
from apps.seguradoras.models import Seguradora


class ModalidadeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Modalidade
        fields = (
            "id",
            "nome",
            "ativo",
            "criado_em",
            "atualizado_em",
        )
        read_only_fields = ("id", "criado_em", "atualizado_em")


class ModalidadeSeguradoraSerializer(serializers.ModelSerializer):
    seguradora = serializers.PrimaryKeyRelatedField(queryset=Seguradora.objects.all())

    # Leitura: o que a tela de mapeamento precisa mostrar.
    seguradora_nome = serializers.CharField(source="seguradora.nome", read_only=True)
    seguradora_ativo = serializers.BooleanField(
        source="seguradora.ativo", read_only=True
    )

    class Meta:
        model = ModalidadeSeguradora
        fields = [
            "id",
            "seguradora",
            "seguradora_nome",
            "seguradora_ativo",
            "codigo_seguradora",
            "ativo",
            "criado_em",
            "atualizado_em",
        ]
        read_only_fields = ["id", "criado_em", "atualizado_em"]


class ModalidadeSeguradoraBulkItemSerializer(serializers.Serializer):
    """Uma célula da matriz.

    `codigo_seguradora` aceita vazio de propósito: é como a tela apaga o
    mapeamento, marcando que a seguradora não oferece a modalidade.
    """

    seguradora = serializers.PrimaryKeyRelatedField(queryset=Seguradora.objects.all())
    codigo_seguradora = serializers.CharField(
        max_length=50, allow_blank=True, required=False, default=""
    )
    ativo = serializers.BooleanField(required=False, default=True)


class ModalidadeSeguradoraBulkSerializer(serializers.Serializer):
    """Códigos de várias seguradoras para uma mesma modalidade."""

    itens = ModalidadeSeguradoraBulkItemSerializer(many=True)

    def validate_itens(self, value):
        vistos = set()
        for item in value:
            seguradora = item["seguradora"]
            if seguradora.pk in vistos:
                raise serializers.ValidationError(
                    f"Seguradora {seguradora.nome} repetida na lista."
                )
            vistos.add(seguradora.pk)
        return value


class MatrizLinhaSerializer(serializers.Serializer):
    """Uma linha da matriz: a modalidade e seus códigos em cada seguradora."""

    modalidade = serializers.PrimaryKeyRelatedField(queryset=Modalidade.objects.all())
    itens = ModalidadeSeguradoraBulkItemSerializer(many=True)

    def validate_itens(self, value):
        vistos = set()
        for item in value:
            seguradora = item["seguradora"]
            if seguradora.pk in vistos:
                raise serializers.ValidationError(
                    f"Seguradora {seguradora.nome} repetida na linha."
                )
            vistos.add(seguradora.pk)
        return value


class MatrizSerializer(serializers.Serializer):
    """A matriz inteira, como a tela salva de uma vez."""

    linhas = MatrizLinhaSerializer(many=True)

    def validate_linhas(self, value):
        vistas = set()
        for linha in value:
            modalidade = linha["modalidade"]
            if modalidade.pk in vistas:
                raise serializers.ValidationError(
                    f"Modalidade {modalidade.nome} repetida na matriz."
                )
            vistas.add(modalidade.pk)
        return value
