import os
import sys

import django

sys.path.append('/home/desenvolvedor/Documentos/cajuina/cajuina_api')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.seguradoras.models import Seguradora  # noqa: E402
from shared.integracoes.junto.client import JuntoClient  # noqa: E402

if __name__ == '__main__':
    seg = Seguradora.objects.get(pk=4)
    client = JuntoClient(seg)

    dados = {"federalId": "07137727000164"}
    print("Sending:", dados)
    try:
        response = client._request("POST", "/guarantee/api/v2/policyholders", json=dados)
        print("Status:", response.status_code)
        print("Response text:", response.text)
    except Exception:
        import traceback
        traceback.print_exc()
