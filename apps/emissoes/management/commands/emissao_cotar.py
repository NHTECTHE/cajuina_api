"""Roda o passo 1 pelo shell, sem servidor nem token JWT.

Existe para testar a integração contra o sandbox durante o desenvolvimento:
`python manage.py emissao_cotar 12 8` (cotação 12, seguradora 8).
"""

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from apps.cotacoes.models import Cotacao
from apps.emissoes import services
from apps.emissoes.conectores.base import ErroSeguradora
from apps.seguradoras.models import Seguradora
from shared.utils import formatar_brl


class Command(BaseCommand):
    help = "Cria ou recalcula na seguradora informada a cotação (passo 1 da emissão)."

    def add_arguments(self, parser):
        parser.add_argument("cotacao_id", type=int)
        parser.add_argument("seguradora_id", type=int)

    def handle(self, *args, **options):
        cotacao_id = options["cotacao_id"]
        seguradora_id = options["seguradora_id"]
        try:
            emissao = services.emissao_cotar(
                cotacao_id=cotacao_id, seguradora_id=seguradora_id
            )
        except Cotacao.DoesNotExist:
            raise CommandError(f"Cotação #{cotacao_id} não existe.") from None
        except Seguradora.DoesNotExist:
            raise CommandError(f"Seguradora #{seguradora_id} não existe.") from None
        except ValidationError as exc:
            raise CommandError(exc.messages[0]) from None
        except ErroSeguradora as exc:
            raise CommandError(str(exc)) from None

        escrever = self.stdout.write
        escrever(self.style.SUCCESS(f"Cotação criada na {emissao.seguradora.nome}"))
        escrever(f"  ambiente ............. {emissao.ambiente}")
        escrever(f"  id na seguradora ..... {emissao.external_id}")
        escrever(f"  prêmio líquido ....... {formatar_brl(emissao.premio_liquido)}")
        escrever(f"  prêmio total ......... {formatar_brl(emissao.premio_total)}")
        escrever(f"  taxa ................. {emissao.taxa}")
        escrever(
            f"  comissão ............. {emissao.comissao_percentual}% "
            f"({formatar_brl(emissao.comissao_valor)})"
        )
        escrever(f"  parcelas sugeridas ... {emissao.numero_parcelas}")
        escrever(f"  opções de parcelamento {len(emissao.opcoes_parcelamento)}")
        if emissao.url_cotacao:
            escrever(f"  url .................. {emissao.url_cotacao}")
