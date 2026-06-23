from .models import Segurado


def segurado_create(*, data: dict) -> Segurado:
    return Segurado.objects.create(**data)


def segurado_update(*, segurado: Segurado, data: dict) -> Segurado:
    for field, value in data.items():
        setattr(segurado, field, value)
    segurado.save()
    return segurado


def segurado_delete(*, segurado: Segurado) -> None:
    segurado.delete()
