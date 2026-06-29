from typing import Dict, Any
from .models import Modalidade

def modalidade_create(*, data: Dict[str, Any]) -> Modalidade:
    modalidade = Modalidade(**data)
    modalidade.save()
    return modalidade

def modalidade_update(*, modalidade: Modalidade, data: Dict[str, Any]) -> Modalidade:
    for field, value in data.items():
        setattr(modalidade, field, value)
    modalidade.save()
    return modalidade

def modalidade_delete(*, modalidade: Modalidade) -> None:
    modalidade.delete()
