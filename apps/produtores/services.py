from .models import Produtor


def produtor_create(*, data: dict) -> Produtor:
    return Produtor.objects.create(**data)


def produtor_update(*, produtor: Produtor, data: dict) -> Produtor:
    for field, value in data.items():
        setattr(produtor, field, value)
    produtor.save()
    return produtor


def produtor_delete(*, produtor: Produtor) -> None:
    produtor.delete()
