from django.apps import AppConfig


class AtividadesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.atividades'

    def ready(self):
        # Import com efeito colateral: registra os receivers de post_save/post_delete
        # que alimentam o log de atividades. O `noqa` é necessário porque o import
        # não tem uso léxico — removê-lo desliga o rastreamento inteiro.
        import apps.atividades.signals  # noqa: F401

