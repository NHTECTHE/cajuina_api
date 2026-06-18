from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.core.mail import send_mail
from django.conf import settings
from .serializers import RegisterSerializer, ActivationSerializer, UserSerializer

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        frontend_url = "http://localhost:3000"
        activation_link = f"{frontend_url}/ativar?token={user.activation_token}"
        
        try:
            send_mail(
                subject='Ativação de Conta - Cajuína',
                message=f'Olá {user.first_name},\n\nClique no link abaixo para ativar sua conta no sistema:\n{activation_link}',
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'nao-responda@cajuina.com.br'),
                recipient_list=[user.email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"Erro ao enviar e-mail: {e}")

        return Response(
            {"message": "Usuário criado com sucesso. Verifique seu e-mail para ativar a conta."},
            status=status.HTTP_201_CREATED
        )

class ActivateView(generics.GenericAPIView):
    serializer_class = ActivationSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(
            {"message": "Conta ativada com sucesso!"},
            status=status.HTTP_200_OK
        )

class UserMeView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user
