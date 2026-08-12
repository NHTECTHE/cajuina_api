from rest_framework.permissions import BasePermission

# Cargos habilitados a disparar comunicação em nome da corretora.
#
# `usuario` fica de fora de propósito: é o cargo default de quem se cadastra
# sozinho em POST /api/v1/users/register/ (AllowAny), então incluí-lo aqui
# devolveria o envio para qualquer pessoa da internet — que é exatamente o
# furo que esta permissão fecha.
CARGOS_COMUNICACAO = frozenset(
    {
        "administrador",
        "financeiro",
        "corretor",
        "produtor",
    }
)


class PodeEnviarComunicacao(BasePermission):
    """Restringe o envio de e-mail ao cliente aos cargos internos.

    Superusuário passa direto: os admins do sistema hoje têm `cargo='usuario'`,
    e barrá-los aqui deixaria a funcionalidade sem ninguém.
    """

    message = "Seu perfil não tem permissão para enviar comunicações ao cliente."

    def has_permission(self, request, view) -> bool:
        usuario = request.user
        if not (usuario and usuario.is_authenticated):
            return False
        if usuario.is_superuser:
            return True
        return usuario.cargo in CARGOS_COMUNICACAO
