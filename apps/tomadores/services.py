from .models import Tomador, ContatoAdicional, Socio


def tomador_create(*, data: dict) -> Tomador:
    contatos = data.pop("contatos_adicionais", [])
    socios = data.pop("socios", [])

    tomador = Tomador.objects.create(**data)

    _sync_contatos(tomador, contatos)
    _sync_socios(tomador, socios)

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
