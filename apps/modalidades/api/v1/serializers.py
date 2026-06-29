from rest_framework import serializers
from apps.modalidades.models import Modalidade

class ModalidadeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Modalidade
        fields = (
            'id',
            'nome',
            'ativo',
            'criado_em',
            'atualizado_em',
        )
        read_only_fields = ('id', 'criado_em', 'atualizado_em')
