from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import BadHeaderError, send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.template.exceptions import TemplateDoesNotExist

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
        except (BadHeaderError, Exception):
            user.delete()
            raise serializers.ValidationError(
                "Não foi possível enviar o e-mail de ativação. Tente novamente mais tarde."
            )

        return user


class EmailOrUsernameTokenSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        credential = attrs.get("username", "")
        if "@" in credential:
            try:
                user_obj = User.objects.get(email=credential)
                attrs["username"] = user_obj.username
            except User.DoesNotExist:
                pass
        return super().validate(attrs)


class UserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'first_name', 'email', 'username', 'cargo')


class UserAdminSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ('id', 'first_name', 'email', 'username', 'cargo', 'password')

    def validate_username(self, value):
        qs = User.objects.filter(username=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Este usuário já está cadastrado.")
        return value

    def validate_email(self, value):
        qs = User.objects.filter(email=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Este e-mail já está cadastrado.")
        return value

    def create(self, validated_data):
        password = validated_data.pop('password', '123456')
        user = User(**validated_data, is_active=True)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance

class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def save(self):
        email = self.validated_data['email']
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        reset_url = f"{frontend_url}/redefinir-senha?uid={uid}&token={token}"
        
        try:
            html_message = render_to_string('users/password_reset_email.html', {'reset_url': reset_url, 'user': user})
            text_message = render_to_string('users/password_reset_email.txt', {'reset_url': reset_url, 'user': user})
        except TemplateDoesNotExist:
            text_message = f"Olá, {user.first_name}.\n\nVocê solicitou a redefinição da sua senha. Acesse o link abaixo para criar uma nova senha:\n{reset_url}\n\nSe você não solicitou, por favor ignore este e-mail."
            html_message = f"<p>Olá, {user.first_name}.</p><p>Você solicitou a redefinição da sua senha. Acesse o link abaixo para criar uma nova senha:</p><p><a href='{reset_url}'>Redefinir Senha</a></p><p>Se você não solicitou, por favor ignore este e-mail.</p>"

        try:
            send_mail(
                subject="Redefinição de Senha - Cajuína",
                message=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
        except Exception as e:
            print(f"Error sending password reset email: {e}")

class PasswordResetConfirmSerializer(serializers.Serializer):
    uidb64 = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8)
    confirm_password = serializers.CharField(min_length=8)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "As senhas não coincidem."})

        try:
            uid = force_str(urlsafe_base64_decode(attrs['uidb64']))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError({"error": "Link inválido ou expirado."})

        if not default_token_generator.check_token(user, attrs['token']):
            raise serializers.ValidationError({"error": "Link inválido ou expirado."})

        self.user = user
        return attrs

    def save(self):
        self.user.set_password(self.validated_data['new_password'])
        self.user.save()

