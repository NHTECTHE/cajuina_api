from rest_framework import serializers
from apps.tomadores.models import Tomador, ContatoAdicional, Socio


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
    qualificacao = serializers.CharField(max_length=50, required=False, allow_blank=True)

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
            "criado_em",
            "atualizado_em",
        ]
        read_only_fields = ["id", "criado_em", "atualizado_em"]

    def validate_cnpj(self, value: str) -> str:
        # Normalise to digits-only for uniqueness check, but store formatted
        return value.strip()
