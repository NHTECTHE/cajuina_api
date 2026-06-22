from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail
from django.core.mail import BadHeaderError
from django.conf import settings
from django.template.loader import render_to_string
from django.template.exceptions import TemplateDoesNotExist
from django.urls import reverse

User = get_user_model()

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    first_name = serializers.CharField(required=True)

    class Meta:
        model = User
        fields = ('cnpj', 'first_name', 'email', 'telefone', 'password')

    def validate_cnpj(self, value):
        if User.objects.filter(cnpj=value).exists():
            raise serializers.ValidationError("Este CNPJ já está cadastrado.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Este E-mail já está cadastrado.")
        return value

    def create(self, validated_data):
        # O username será o próprio email para evitar conflitos de unique
        username = validated_data['email']
        user = User(
            username=username,
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            cnpj=validated_data.get('cnpj'),
            telefone=validated_data.get('telefone'),
            is_active=False
        )
        user.set_password(validated_data['password'])
        user.save()

        # Gerar token e link de ativação
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        
        # O link de ativação será processado pelo backend e redirecionará para o front
        # O HOST_URL pode vir do settings ou usar um fallback local
        host = getattr(settings, 'API_HOST', 'http://localhost:8000')
        activation_url = f"{host}/api/v1/users/activate/{uid}/{token}/"

        try:
            html_message = render_to_string('users/activation_email.html', {'activation_url': activation_url, 'user': user})
            text_message = render_to_string('users/activation_email.txt', {'activation_url': activation_url, 'user': user})
        except TemplateDoesNotExist:
            text_message = f"Olá, {user.first_name}.\n\nPor favor, ative sua conta através do link:\n{activation_url}"
            html_message = f"<p>Olá, {user.first_name}.</p><p>Por favor, ative sua conta através do link:</p><p><a href='{activation_url}'>Ativar Conta</a></p>"

        try:
            send_mail(
                subject="Ativação de Conta - Cajuína",
                message=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
        except (BadHeaderError, Exception) as e:
            user.delete()
            raise serializers.ValidationError(
                "Não foi possível enviar o e-mail de ativação. Tente novamente mais tarde."
            )

        return user
