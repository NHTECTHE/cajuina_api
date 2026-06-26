from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from apps.atividades.middleware import get_current_user
from apps.atividades.services import atividade_create

TRACKED_MODELS = ['CustomUser', 'Tomador', 'Corretor', 'Segurado', 'Produtor', 'Seguradora', 'Modalidade']

def get_entity_name(model_name):
    mapping = {
        'CustomUser': 'Usuário',
        'Tomador': 'Tomador',
        'Corretor': 'Corretor',
        'Segurado': 'Segurado',
        'Produtor': 'Produtor',
        'Seguradora': 'Seguradora',
        'Modalidade': 'Modalidade',
    }
    return mapping.get(model_name, model_name)

def get_item_description(instance):
    if hasattr(instance, 'nome') and getattr(instance, 'nome'):
        return instance.nome
    if hasattr(instance, 'first_name') and getattr(instance, 'first_name'):
        return instance.first_name
    return str(instance)

def get_changed_fields(instance):
    if not instance.pk:
        return []
    try:
        old_instance = instance.__class__.objects.get(pk=instance.pk)
        changed = []
        for field in instance._meta.fields:
            field_name = field.name
            if field_name in ['criado_em', 'atualizado_em']:
                continue
            if getattr(instance, field_name) != getattr(old_instance, field_name):
                changed.append(field_name)
        return changed
    except Exception:
        return []

@receiver(pre_save)
def track_changes(sender, instance, **kwargs):
    model_name = sender.__name__
    if model_name not in TRACKED_MODELS:
        return
    instance._changed_fields = get_changed_fields(instance)

@receiver(post_save)
def log_save(sender, instance, created, **kwargs):
    model_name = sender.__name__
    if model_name not in TRACKED_MODELS:
        return

    # Avoid logging user creation during signup/activation if there is no logged in user, or log as "Sistema"
    user = get_current_user()

    acao = "CRIAÇÃO" if created else "ATUALIZAÇÃO"
    entidade = get_entity_name(model_name)
    item = get_item_description(instance)

    detalhes = ""
    if not created:
        changed_fields = getattr(instance, '_changed_fields', [])
        if changed_fields:
            filtered_fields = [f for f in changed_fields if f not in ['password', 'last_login']]
            if filtered_fields:
                detalhes = f"Campos alterados: {', '.join(filtered_fields)}"
            else:
                if 'password' in changed_fields:
                    detalhes = "Campos alterados: password"
                else:
                    return # Skip if it was just last_login/etc.
        else:
            detalhes = "Campos alterados: atualizado_em"

    atividade_create(
        usuario=user,
        acao=acao,
        entidade=entidade,
        item=item,
        detalhes=detalhes
    )

@receiver(post_delete)
def log_delete(sender, instance, **kwargs):
    model_name = sender.__name__
    if model_name not in TRACKED_MODELS:
        return

    user = get_current_user()
    entidade = get_entity_name(model_name)
    item = get_item_description(instance)

    atividade_create(
        usuario=user,
        acao="EXCLUSÃO",
        entidade=entidade,
        item=item,
        detalhes=""
    )
