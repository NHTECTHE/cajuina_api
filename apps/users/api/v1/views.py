from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from django.shortcuts import redirect
from django.conf import settings
from django.db.models import Q

from .serializers import UserRegistrationSerializer, EmailOrUsernameTokenSerializer, UserListSerializer, UserAdminSerializer

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
            return redirect(f"{frontend_url}/?activation=success")
        else:
            return redirect(f"{frontend_url}/?activation=error")

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


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailOrUsernameTokenSerializer


def _envelope(data):
    return {"data": data}

class UserListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        search = request.query_params.get("search", "")
        qs = User.objects.all().order_by("first_name")
        if search:
            qs = qs.filter(
                Q(first_name__icontains=search) |
                Q(email__icontains=search) |
                Q(username__icontains=search)
            )
        serializer = UserListSerializer(qs, many=True)
        return Response(_envelope(serializer.data))

    def post(self, request):
        serializer = UserAdminSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        out = UserListSerializer(user)
        return Response(_envelope(out.data), status=status.HTTP_201_CREATED)


class UserDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_object(self, pk):
        from rest_framework.exceptions import NotFound
        try:
            return User.objects.get(pk=pk)
        except User.DoesNotExist:
            raise NotFound(detail="Usuário não encontrado.")

    def get(self, request, pk):
        user = self._get_object(pk)
        return Response(_envelope(UserListSerializer(user).data))

    def patch(self, request, pk):
        user = self._get_object(pk)
        serializer = UserAdminSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(_envelope(UserListSerializer(user).data))

    def delete(self, request, pk):
        user = self._get_object(pk)
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
