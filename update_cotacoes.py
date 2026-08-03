from apps.cotacoes.models import Cotacao
updated = Cotacao.objects.filter(status="Iniciado").update(status="Aprovado")
print(f"Updated {updated} cotacoes.")
