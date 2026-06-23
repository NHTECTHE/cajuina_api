from .models import Corretor


def corretor_create(*, data: dict) -> Corretor:
    return Corretor.objects.create(**data)


def corretor_update(*, corretor: Corretor, data: dict) -> Corretor:
    for field, value in data.items():
        setattr(corretor, field, value)
    corretor.save()
    return corretor


def corretor_delete(*, corretor: Corretor) -> None:
    corretor.delete()
