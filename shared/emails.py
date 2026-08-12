import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


class EnvioEmailError(Exception):
    """Falha na entrega ao servidor SMTP."""


def enviar_email(*, assunto: str, mensagem: str, destinatario: str) -> None:
    """Envia um e-mail já montado pelo servidor.

    Nenhum dos argumentos deve vir direto do corpo da request: quem chama é
    responsável por derivá-los do objeto (cotação/apólice). Ver
    `cotacao_montar_email` / `apolice_montar_email`.
    """
    try:
        send_mail(
            subject=assunto,
            message=mensagem,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[destinatario],
            fail_silently=False,
        )
    except Exception as exc:
        # A exceção do SMTP carrega host, usuário e detalhe do provedor. Fica no
        # log do servidor; a resposta ao cliente é genérica.
        logger.exception("Falha ao enviar e-mail para %s", destinatario)
        raise EnvioEmailError from exc
