from .models import Atividade

def atividade_create(*, usuario=None, acao: str, entidade: str, item: str, detalhes: str = "") -> Atividade:
    nome = ""
    username = ""
    if usuario:
        nome = usuario.first_name if usuario.first_name else usuario.username
        username = usuario.username
    else:
        nome = "Sistema"
        username = "sistema"

    atividade = Atividade(
        usuario=usuario,
        usuario_nome=nome,
        usuario_username=username,
        acao=acao,
        entidade=entidade,
        item=item,
        detalhes=detalhes
    )
    atividade.save()
    return atividade
