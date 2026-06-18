from rest_framework import serializers
from apps.tomador.models import Tomador, Socio, ContatoAdicional

class SocioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Socio
        fields = ['id', 'nome', 'cpf', 'email', 'telefone']

class ContatoAdicionalSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContatoAdicional
        fields = ['id', 'nome', 'email', 'telefone', 'cargo']

class TomadorSerializer(serializers.ModelSerializer):
    socios = SocioSerializer(many=True, required=False)
    contatos_adicionais = ContatoAdicionalSerializer(many=True, required=False, source='contatos')

    class Meta:
        model = Tomador
        fields = '__all__'

    def validate_cnpj(self, value):
        if value:
            return value.strip()
        return value

    def create(self, validated_data):
        socios_data = validated_data.pop('socios', [])
        contatos_data = validated_data.pop('contatos', [])
        
        tomador = Tomador.objects.create(**validated_data)
        
        for socio_data in socios_data:
            Socio.objects.create(tomador=tomador, **socio_data)
            
        for contato_data in contatos_data:
            ContatoAdicional.objects.create(tomador=tomador, **contato_data)
            
        return tomador

    def update(self, instance, validated_data):
        socios_data = validated_data.pop('socios', None)
        contatos_data = validated_data.pop('contatos', None)

        # Atualiza os campos simples
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Atualiza os sócios (substitui os antigos)
        if socios_data is not None:
            instance.socios.all().delete()
            for socio_data in socios_data:
                Socio.objects.create(tomador=instance, **socio_data)

        # Atualiza os contatos (substitui os antigos)
        if contatos_data is not None:
            instance.contatos.all().delete()
            for contato_data in contatos_data:
                ContatoAdicional.objects.create(tomador=instance, **contato_data)

        return instance
