from rest_framework import serializers
from .models import Atividade

class AtividadeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Atividade
        fields = '__all__'
