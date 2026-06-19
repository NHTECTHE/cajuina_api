from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from django.shortcuts import redirect
from django.conf import settings

from .serializers import UserRegistrationSerializer

User = get_user_model()

class UserRegistrationView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

class UserActivationView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, uidb64, token):
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')

        if user is not None and default_token_generator.check_token(user, token):
            user.is_active = True
            user.save()
            # Redireciona para o login do frontend com uma query de sucesso
            return redirect(f"{frontend_url}/?activation=success")
        else:
            # Redireciona para o frontend com erro
            return redirect(f"{frontend_url}/?activation=error")

from rest_framework.permissions import IsAuthenticated

class UserMeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            "id": user.id,
            "first_name": user.first_name,
            "email": user.email,
            "cnpj": user.cnpj,
            "telefone": user.telefone,
            "is_superuser": user.is_superuser,
        })
