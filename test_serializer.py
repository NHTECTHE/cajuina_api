import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from apps.tomador.api.v1.serializers import TomadorSerializer

payload = {
  "cnpj": "00.000.000/0000-00",
  "nome": "TESTE",
  "nome_fantasia": "",
  "produtor": "CAJUINA SEGUROS",
  "corretora": "CAJUINA",
  "cidade": "TERESINA",
  "uf": "PI",
  "contato": "TESTE",
  "celular": "",
  "email": "",
  "habilitar_email": False,
  "telefone": "",
  "observacoes": "",
  "ativar_cotacao": False,
  "endereco": "",
  "bairro": "",
  "numero": "",
  "complemento": "",
  "cep": "",
  "contatos_adicionais": [],
  "socios": []
}

serializer = TomadorSerializer(data=payload)
if not serializer.is_valid():
    print("ERRORS:", serializer.errors)
else:
    print("VALID!")
