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

    class Meta:
        model = Socio
        fields = ["id", "nome", "cpf", "nascimento", "qualificacao"]


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
