from rest_framework import serializers

from apps.seguradoras.models import Seguradora
from apps.tomadores.models import (
    ContatoAdicional,
    Socio,
    Tomador,
    TomadorArquivo,
    TomadorSeguradora,
)

MAX_ARQUIVO_SIZE = 20 * 1024 * 1024  # 20MB


class TomadorArquivoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TomadorArquivo
        fields = ["id", "arquivo", "nome_original", "tamanho", "criado_em"]
        read_only_fields = ["id", "nome_original", "tamanho", "criado_em"]

    def validate_arquivo(self, value):
        if value.size > MAX_ARQUIVO_SIZE:
            raise serializers.ValidationError(
                "Arquivo excede o tamanho máximo de 20MB."
            )
        return value


class ContatoAdicionalSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContatoAdicional
        fields = ["id", "nome", "telefone", "email"]


class SocioSerializer(serializers.ModelSerializer):
    nascimento = serializers.DateField(
        format="%Y-%m-%d",
        input_formats=["%Y-%m-%d", "%d/%m/%Y"],
        allow_null=True,
        required=False,
    )
    # Sobrescrevemos qualificacao para ignorar o choices_validation se vier dado externo (ex: "10-Diretor")
    qualificacao = serializers.CharField(
        max_length=50, required=False, allow_blank=True
    )

    class Meta:
        model = Socio
        fields = ["id", "nome", "cpf", "nascimento", "qualificacao"]

    def to_internal_value(self, data):
        # Transforma strings vazias de nascimento em None
        if "nascimento" in data and data["nascimento"] == "":
            data = data.copy()
            data["nascimento"] = None
        return super().to_internal_value(data)


class TomadorSerializer(serializers.ModelSerializer):
    contatos_adicionais = ContatoAdicionalSerializer(many=True, required=False)
    socios = SocioSerializer(many=True, required=False)
    criado_por_nome = serializers.SerializerMethodField()

    class Meta:
        model = Tomador
        fields = [
            "id",
            "cnpj",
            "nome",
            "nome_fantasia",
            "produtor",
            "corretora",
            "contato",
            "email",
            "habilitar_email",
            "telefone",
            "celular",
            "cep",
            "endereco",
            "numero",
            "complemento",
            "bairro",
            "cidade",
            "uf",
            "ativar_cotacao",
            "observacoes",
            "contatos_adicionais",
            "socios",
            "criado_por_nome",
            "criado_em",
            "atualizado_em",
        ]
        read_only_fields = ["id", "criado_por_nome", "criado_em", "atualizado_em"]

    def validate_cnpj(self, value: str) -> str:
        # Normalise to digits-only for uniqueness check, but store formatted
        return value.strip()

    def get_criado_por_nome(self, obj) -> str | None:
        if not obj.criado_por:
            return None
        return obj.criado_por.first_name or obj.criado_por.email


class TomadorSeguradoraSerializer(serializers.ModelSerializer):
    seguradora = serializers.PrimaryKeyRelatedField(queryset=Seguradora.objects.all())

    # Leitura: dados prontos para a tela de taxas do tomador.
    seguradora_nome = serializers.CharField(source="seguradora.nome", read_only=True)
    seguradora_ativo = serializers.BooleanField(
        source="seguradora.ativo", read_only=True
    )
    apto = serializers.BooleanField(read_only=True)
    premio_minimo_efetivo = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True
    )
    dias_vencimento_efetivo = serializers.IntegerField(read_only=True)

    class Meta:
        model = TomadorSeguradora
        fields = [
            "id",
            "seguradora",
            "seguradora_nome",
            "seguradora_ativo",
            "status",
            "taxa",
            "premio_minimo",
            "premio_minimo_efetivo",
            "dias_vencimento",
            "dias_vencimento_efetivo",
            "apto",
            "criado_em",
            "atualizado_em",
        ]
        read_only_fields = ["id", "criado_em", "atualizado_em"]


class TomadorSeguradoraBulkSerializer(serializers.Serializer):
    """Recebe a lista de condições enviada pela tela de taxas do tomador."""

    itens = TomadorSeguradoraSerializer(many=True)

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
