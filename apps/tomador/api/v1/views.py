from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.tomador.models import Tomador
from apps.tomador.api.v1.serializers import TomadorSerializer

class TomadorViewSet(viewsets.ModelViewSet):
    queryset = Tomador.objects.all().order_by('-created_at')
    serializer_class = TomadorSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print("VALIDATION ERRORS:", serializer.errors)
        return super().create(request, *args, **kwargs)
