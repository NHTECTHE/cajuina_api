from .models import Seguradora


def seguradora_create(*, data: dict) -> Seguradora:
    return Seguradora.objects.create(**data)


def seguradora_update(*, seguradora: Seguradora, data: dict) -> Seguradora:
    for field, value in data.items():
        setattr(seguradora, field, value)
    seguradora.save()
    return seguradora


def seguradora_delete(*, seguradora: Seguradora) -> None:
    seguradora.delete()
