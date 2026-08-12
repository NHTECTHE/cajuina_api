from rest_framework import serializers


class EnvioEmailSerializer(serializers.Serializer):
    """Entrada dos endpoints de envio de e-mail.

    É deliberadamente mínimo: destinatário, assunto e corpo são montados pelo
    servidor a partir do objeto. O único texto livre é `observacao`, que vai
    para uma seção identificada no fim da mensagem — e é limitado para não
    virar um corpo de e-mail inteiro por outro caminho.
    """

    observacao = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
        trim_whitespace=True,
    )
