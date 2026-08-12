from .models import Atividade


def atividade_create(
    *,
    usuario=None,
    acao: str,
    entidade: str,
    object_id: int | None = None,
    item: str,
    detalhes: str = "",
) -> Atividade:
    if usuario:
        nome = usuario.first_name or usuario.email
    else:
        nome = "Sistema"

    atividade = Atividade(
        usuario=usuario,
        usuario_nome=nome,
        acao=acao,
        entidade=entidade,
        object_id=object_id,
        item=item,
        detalhes=detalhes,
    )
    atividade.save()
    return atividade
