from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Atividade
from .serializers import AtividadeSerializer

class AtividadeListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        atividades = Atividade.objects.all().order_by('-criado_em')
        serializer = AtividadeSerializer(atividades, many=True)
        return Response({"data": serializer.data})
