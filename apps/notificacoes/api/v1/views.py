from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notificacoes.models import Notificacao

from .serializers import NotificacaoSerializer


class NotificacaoListView(generics.ListAPIView):
    serializer_class = NotificacaoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notificacao.objects.filter(usuario=self.request.user)[:50]

class NotificacaoMarcarLidasView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        Notificacao.objects.filter(usuario=request.user, lida=False).update(lida=True)
        return Response({"detail": "Notificações marcadas como lidas."}, status=status.HTTP_200_OK)
