from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'email', 'is_superuser', 'cnpj', 'telefone')

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    
    class Meta:
        model = User
        fields = ('cnpj', 'first_name', 'email', 'telefone', 'password')
        extra_kwargs = {
            'first_name': {'required': True},
            'email': {'required': True},
            'cnpj': {'required': True},
            'telefone': {'required': True},
        }

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Este e-mail já está em uso.")
        return value

    def validate_cnpj(self, value):
        if User.objects.filter(cnpj=value).exists():
            raise serializers.ValidationError("Este CNPJ já está cadastrado.")
        return value

    def validate_first_name(self, value):
        # Valida se o nome contém caracteres inválidos para o login (ex: espaços)
        import re
        if not re.match(r'^[\w.@+-]+\Z', value):
            raise serializers.ValidationError("O nome de usuário não pode conter espaços e deve usar apenas letras, números ou @/./+/-/_")
        
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Este nome de usuário já está em uso.")
        return value

    def create(self, validated_data):
        user = User.objects.create(
            username=validated_data['first_name'],  # Utiliza o nome digitado como username
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            cnpj=validated_data['cnpj'],
            telefone=validated_data['telefone'],
            is_active=False  # O usuário é criado como inativo
        )
        user.set_password(validated_data['password'])
        user.save()
        return user


class ActivationSerializer(serializers.Serializer):
    token = serializers.UUIDField(required=True)

    def validate_token(self, value):
        try:
            user = User.objects.get(activation_token=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("Token de ativação inválido ou já utilizado.")
        
        if user.is_active:
            raise serializers.ValidationError("Esta conta já está ativa.")
            
        self.context['user'] = user
        return value

    def save(self):
        user = self.context['user']
        user.is_active = True
        user.activation_token = None
        user.save()
        return user
