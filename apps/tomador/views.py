import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

class CnpjProxyView(APIView):
    def get(self, request, cnpj: str):
        cnpj_digits = "".join(filter(str.isdigit, cnpj)) # Apenas números
        if len(cnpj_digits) != 14:
            return Response({"detail": "CNPJ inválido"}, status=status.HTTP_400_BAD_REQUEST)

        cnpja_url = f"https://open.cnpja.com/office/{cnpj_digits}"
        brasil_api_url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_digits}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }

        try:
            cnpja_response = requests.get(cnpja_url, headers=headers, timeout=10)
            if cnpja_response.status_code == 200:
                return Response({"source": "cnpja", "data": cnpja_response.json()}, status=status.HTTP_200_OK)
        except requests.RequestException:
            pass

        try:
            brasil_api_response = requests.get(brasil_api_url, headers=headers, timeout=10)
            if brasil_api_response.status_code == 200:
                return Response(
                    {"source": "brasilapi", "data": brasil_api_response.json()},
                    status=status.HTTP_200_OK,
                )
            if brasil_api_response.status_code == 404:
                return Response({"detail": "CNPJ não encontrado"}, status=status.HTTP_404_NOT_FOUND)
        except requests.RequestException:
            pass

        return Response({"detail": "Falha ao consultar serviços de CNPJ"}, status=status.HTTP_502_BAD_GATEWAY)
