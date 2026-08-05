from django.contrib.auth import get_user_model
from django.db import transaction

from apps.notificacoes.models import Notificacao

from .models import ContatoAdicional, Socio, Tomador, TomadorArquivo, TomadorSeguradora


def tomador_create(*, data: dict, criado_por=None) -> Tomador:
    contatos = data.pop("contatos_adicionais", [])
    socios = data.pop("socios", [])

    tomador = Tomador.objects.create(**data, criado_por=criado_por)

    _sync_contatos(tomador, contatos)
    _sync_socios(tomador, socios)

    # Notify admins
    # Notify all users
    User = get_user_model()
    users_to_notify = User.objects.all()
    nome_exibicao = tomador.nome_fantasia if tomador.nome_fantasia else tomador.nome
    for user in users_to_notify:
        Notificacao.objects.create(
            usuario=user,
            titulo="Novo tomador cadastrado",
            status_badge="NOVO",
            mensagem=nome_exibicao
        )

    return tomador


def tomador_update(*, tomador: Tomador, data: dict) -> Tomador:
    contatos = data.pop("contatos_adicionais", None)
    socios = data.pop("socios", None)

    for field, value in data.items():
        setattr(tomador, field, value)
    tomador.save()

    if contatos is not None:
        tomador.contatos_adicionais.all().delete()
        _sync_contatos(tomador, contatos)

    if socios is not None:
        tomador.socios.all().delete()
        _sync_socios(tomador, socios)

    return tomador


def tomador_delete(*, tomador: Tomador) -> None:
    tomador.delete()


def _sync_contatos(tomador: Tomador, contatos: list[dict]) -> None:
    ContatoAdicional.objects.bulk_create([
        ContatoAdicional(tomador=tomador, **c) for c in contatos
    ])


def _sync_socios(tomador: Tomador, socios: list[dict]) -> None:
    Socio.objects.bulk_create([
        Socio(tomador=tomador, **s) for s in socios
    ])


def tomador_arquivo_create(*, tomador: Tomador, arquivo) -> TomadorArquivo:
    return TomadorArquivo.objects.create(
        tomador=tomador,
        arquivo=arquivo,
        nome_original=arquivo.name,
        tamanho=arquivo.size,
    )


def tomador_arquivo_delete(*, arquivo: TomadorArquivo) -> None:
    arquivo.arquivo.delete(save=False)
    arquivo.delete()


def tomador_seguradora_upsert(
    *, tomador: Tomador, seguradora, data: dict
) -> TomadorSeguradora:
    """Cria ou atualiza as condições do par tomador/seguradora.

    A UniqueConstraint do par permite um único update_or_create.
    """
    vinculo, _ = TomadorSeguradora.objects.update_or_create(
        tomador=tomador,
        seguradora=seguradora,
        defaults=data,
    )
    return vinculo


@transaction.atomic
def tomador_seguradora_bulk_upsert(
    *, tomador: Tomador, itens: list[dict]
) -> list[TomadorSeguradora]:
    """Salva as condições de várias seguradoras de uma vez.

    Cada item precisa trazer `seguradora`; os demais campos são opcionais.
    Seguradoras não enviadas ficam intactas.
    """
    resultado = []
    for item in itens:
        data = dict(item)
        seguradora = data.pop("seguradora")
        resultado.append(
            tomador_seguradora_upsert(
                tomador=tomador, seguradora=seguradora, data=data
            )
        )
    return resultado


def tomador_seguradora_delete(*, vinculo: TomadorSeguradora) -> None:
    vinculo.delete()
